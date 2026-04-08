"""Vulnerability scan pipeline — orchestrates scan lifecycle from Cloud Run side."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.package import Package
from app.models.puzzle import Puzzle
from app.models.vulnerability import Vulnerability
from app.models.vulnerability_scan import VulnerabilityScan
from app.services.audit.worker_client import AuditWorkerClient

logger = logging.getLogger(__name__)


async def trigger_vulnerability_scan(
    db: AsyncSession,
    package: Package,
    version_string: str,
    trigger: str = "manual",
) -> VulnerabilityScan:
    """Create a vulnerability scan record and submit to the worker."""
    # Check if a scan already exists for this version
    existing = await db.execute(
        select(VulnerabilityScan).where(
            VulnerabilityScan.package_id == package.id,
            VulnerabilityScan.version_string == version_string,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Scan already exists for {package.name}@{version_string}")

    # Create scan record
    scan = VulnerabilityScan(
        package_id=package.id,
        version_string=version_string,
        status="pending",
        trigger=trigger,
        started_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    await db.flush()

    # Build callback URL
    callback_url = None
    if settings.frontend_url:
        # Use the backend's own URL for callbacks
        backend_base = settings.audit_worker_url.replace(":8080", ":8000") if settings.audit_worker_url else ""
        # Actually use the Cloud Run URL
        callback_url = f"https://ghostapi.validia.ai/api/v1/webhooks/audit-callback"

    # Submit to worker
    try:
        client = AuditWorkerClient()
        await client.submit_audit(
            audit_id=str(scan.id),
            package_name=package.name,
            registry=package.registry,
            version=version_string,
            callback_url=callback_url,
        )
        scan.status = "submitted"
        logger.info("Submitted audit for %s@%s (scan_id=%s)", package.name, version_string, scan.id)
    except Exception as e:
        scan.status = "failed"
        scan.error_message = f"Failed to submit to worker: {e}"
        logger.error("Failed to submit audit for %s: %s", package.name, e)

    await db.commit()
    return scan


async def process_audit_callback(
    db: AsyncSession,
    result: dict,
) -> VulnerabilityScan | None:
    """Process results from the audit worker callback."""
    audit_id = result.get("audit_id")
    if not audit_id:
        logger.error("Callback missing audit_id")
        return None

    # Find the scan
    scan_result = await db.execute(
        select(VulnerabilityScan).where(VulnerabilityScan.id == audit_id)
    )
    scan = scan_result.scalar_one_or_none()
    if not scan:
        logger.error("Scan not found for audit_id=%s", audit_id)
        return None

    # Update scan metadata
    scan.status = result.get("status", "complete")
    scan.source_size_bytes = result.get("source_size_bytes")
    scan.source_file_count = result.get("source_file_count")
    scan.discovery_model = result.get("discovery_model")
    scan.discovery_tokens_used = result.get("discovery_tokens_used")
    scan.discovery_duration_secs = result.get("discovery_duration_secs")
    scan.validation_model = result.get("validation_model")
    scan.validation_tokens_used = result.get("validation_tokens_used")
    scan.validation_duration_secs = result.get("validation_duration_secs")
    scan.total_cost_usd = result.get("total_cost_usd")
    scan.error_message = result.get("error")
    scan.completed_at = datetime.now(timezone.utc)

    # Store raw results
    scan.discovery_result = {"findings": [f for f in result.get("discovery_findings", [])]}
    scan.validation_result = {
        "validated": result.get("validated_vulnerabilities", []),
        "rejected": result.get("rejected_indices", []),
    }

    # Get the package for denormalized fields
    pkg_result = await db.execute(select(Package).where(Package.id == scan.package_id))
    package = pkg_result.scalar_one()

    # Create Vulnerability records for validated findings
    discovery_findings = result.get("discovery_findings", [])
    validated_vulns = result.get("validated_vulnerabilities", [])

    for v in validated_vulns:
        if not v.get("validated", False):
            continue

        idx = v.get("original_index", -1)
        if idx < 0 or idx >= len(discovery_findings):
            continue

        finding = discovery_findings[idx]

        vuln = Vulnerability(
            scan_id=scan.id,
            package_id=scan.package_id,
            category=finding.get("category", "unknown"),
            subcategory=finding.get("subcategory"),
            severity=v.get("severity_adjusted", finding.get("severity", "medium")),
            title=finding.get("title", "Untitled"),
            description=finding.get("description", ""),
            file_path=finding.get("file_path"),
            line_start=finding.get("line_start"),
            line_end=finding.get("line_end"),
            code_snippet=finding.get("code_snippet"),
            poc_code=v.get("poc_code"),
            poc_description=v.get("poc_description"),
            attack_vector=finding.get("attack_vector"),
            impact=finding.get("impact"),
            cvss_score=v.get("cvss_score"),
            cwe_id=finding.get("cwe_id"),
            confidence=v.get("confidence", 0.5),
            validated=True,
            remediation=v.get("remediation"),
            attack_chain=v.get("attack_chain"),
        )
        db.add(vuln)

    await db.flush()

    # Store puzzles — need to map vulnerability_index to actual vuln IDs
    puzzles_data = result.get("puzzles", [])
    if puzzles_data:
        # Build a map from vuln index to the Vulnerability record we just created
        # Re-query to get the IDs
        from sqlalchemy import select as sel
        vuln_records = (await db.execute(
            sel(Vulnerability).where(Vulnerability.scan_id == scan.id)
        )).scalars().all()

        for p in puzzles_data:
            vuln_idx = p.get("vulnerability_index", 0)
            if vuln_idx < len(vuln_records):
                puzzle = Puzzle(
                    vulnerability_id=vuln_records[vuln_idx].id,
                    game_type=p.get("game_type", "maze"),
                    title=p.get("title", "Puzzle"),
                    flavor_text=p.get("flavor_text", ""),
                    level_data=p.get("level_data", {}),
                    difficulty=p.get("difficulty", 3),
                    par_time_secs=p.get("par_time_secs"),
                )
                db.add(puzzle)

    await db.commit()

    vuln_count = len([v for v in validated_vulns if v.get("validated")])
    puzzle_count = len(puzzles_data)
    logger.info(
        "Audit callback processed for %s@%s: %d vulnerabilities, %d puzzles",
        package.name, scan.version_string, vuln_count, puzzle_count,
    )

    return scan
