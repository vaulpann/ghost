"""Ghost Audit Worker — Codex-powered chunked vulnerability scanner.

Runs one targeted Codex session per vulnerability category, each asking
"a researcher said there's an X vulnerability here — was he right?"
Then validates each finding individually with PoC generation.
"""

import asyncio
import json
import logging
import uuid

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.codex_runner import parse_json_from_output, run_codex
from app.config import settings
from app.download import cleanup_source, download_package_source
from app.models import (
    AuditRequest,
    AuditResult,
    AuditStatusResponse,
    DiscoveryFinding,
    ValidatedVulnerability,
)
from app.prompts import DISCOVERY_WRAPPER, VALIDATION_PROMPT, VULN_CATEGORIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("ghost-worker")

app = FastAPI(title="Ghost Audit Worker", version="0.2.0")

_semaphore = asyncio.Semaphore(settings.max_concurrent_audits)
_audits: dict[str, AuditStatusResponse] = {}
_queue_depth = 0


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ghost-audit-worker", "queue_depth": _queue_depth}


@app.post("/audit")
async def submit_audit(req: AuditRequest, background_tasks: BackgroundTasks):
    global _queue_depth
    if _queue_depth >= settings.max_queue_depth:
        raise HTTPException(503, "Queue full")

    audit_id = req.audit_id or str(uuid.uuid4())
    _audits[audit_id] = AuditStatusResponse(audit_id=audit_id, status="accepted")
    _queue_depth += 1
    background_tasks.add_task(_run_audit, audit_id, req)
    return {"audit_id": audit_id, "status": "accepted"}


@app.get("/audit/{audit_id}/status")
async def get_audit_status(audit_id: str):
    if audit_id not in _audits:
        raise HTTPException(404)
    return _audits[audit_id]


async def _run_audit(audit_id: str, req: AuditRequest):
    """Chunked two-pass audit: one Codex session per vuln category, then individual validation."""
    global _queue_depth
    result = AuditResult(audit_id=audit_id, status="running")
    total_discovery_secs = 0.0

    try:
        async with _semaphore:
            # === DOWNLOAD ===
            _audits[audit_id].status = "downloading"
            source_path, size_bytes, file_count = await download_package_source(
                req.package_name, req.version, req.registry, req.tarball_url
            )
            result.source_size_bytes = size_bytes
            result.source_file_count = file_count

            # === TARGETED DISCOVERY — one scan per vuln category ===
            _audits[audit_id].status = "discovery"
            all_findings: list[DiscoveryFinding] = []

            for i, category in enumerate(VULN_CATEGORIES):
                progress = f"Scanning for {category['name']} ({i+1}/{len(VULN_CATEGORIES)})"
                _audits[audit_id].progress = progress
                logger.info("[%s] %s", req.package_name, progress)

                prompt = DISCOVERY_WRAPPER.format(
                    package_name=req.package_name,
                    registry=req.registry,
                    version=req.version,
                    category_name=category["name"],
                    category_prompt=category["prompt"],
                    category_id=category["id"],
                )

                output = await run_codex(
                    prompt=prompt,
                    working_dir=source_path,
                    model=settings.codex_discovery_model,
                    timeout_secs=settings.codex_timeout_secs,
                )
                total_discovery_secs += output["duration_secs"]

                data = parse_json_from_output(output["stdout"])
                if data and data.get("found") and data.get("vulnerabilities"):
                    for v in data["vulnerabilities"]:
                        try:
                            v.setdefault("category", category["id"])
                            all_findings.append(DiscoveryFinding(**v))
                        except Exception as e:
                            logger.warning("Skipping malformed finding: %s", e)

                    logger.info("[%s] %s: %d potential vulns", req.package_name, category["name"], len(data["vulnerabilities"]))
                else:
                    logger.info("[%s] %s: clean", req.package_name, category["name"])

            result.discovery_findings = all_findings
            result.discovery_model = settings.codex_discovery_model
            result.discovery_duration_secs = total_discovery_secs

            logger.info(
                "[%s] Discovery complete: %d findings across %d categories in %.0fs",
                req.package_name, len(all_findings), len(VULN_CATEGORIES), total_discovery_secs,
            )

            if not all_findings:
                result.status = "complete"
                await _send_callback(req.callback_url, result)
                return

            # === VALIDATION — one Codex session per finding ===
            _audits[audit_id].status = "validation"
            credible = [f for f in all_findings if f.confidence >= 0.5]

            if not credible:
                result.status = "complete"
                await _send_callback(req.callback_url, result)
                return

            logger.info("[%s] Validating %d findings...", req.package_name, len(credible))
            total_validation_secs = 0.0

            for idx, finding in enumerate(credible):
                _audits[audit_id].progress = f"Validating finding {idx+1}/{len(credible)}: {finding.title[:50]}"

                validation_prompt = VALIDATION_PROMPT.format(
                    package_name=req.package_name,
                    registry=req.registry,
                    version=req.version,
                    vulnerability_json=json.dumps(finding.model_dump(), indent=2),
                )

                val_output = await run_codex(
                    prompt=validation_prompt,
                    working_dir=source_path,
                    model=settings.codex_validation_model,
                    timeout_secs=settings.codex_timeout_secs,
                )
                total_validation_secs += val_output["duration_secs"]

                val_data = parse_json_from_output(val_output["stdout"])
                if val_data:
                    try:
                        val_data["original_index"] = idx
                        if val_data.get("validated"):
                            result.validated_vulnerabilities.append(ValidatedVulnerability(**val_data))
                            logger.info("[%s] CONFIRMED: %s", req.package_name, finding.title)
                        else:
                            result.rejected_indices.append(idx)
                            logger.info("[%s] Rejected: %s", req.package_name, finding.title)
                    except Exception as e:
                        logger.warning("Validation parse error: %s", e)
                        result.rejected_indices.append(idx)
                else:
                    result.rejected_indices.append(idx)

            result.validation_model = settings.codex_validation_model
            result.validation_duration_secs = total_validation_secs

            logger.info(
                "[%s] Validation complete: %d confirmed, %d rejected in %.0fs",
                req.package_name, len(result.validated_vulnerabilities), len(result.rejected_indices), total_validation_secs,
            )

            result.status = "complete"

    except Exception as e:
        logger.error("[%s] Audit failed: %s", req.package_name, e)
        result.status = "failed"
        result.error = str(e)

    finally:
        _queue_depth -= 1
        _audits[audit_id] = AuditStatusResponse(audit_id=audit_id, status=result.status, error=result.error)
        try:
            cleanup_source(req.package_name, req.version)
        except Exception:
            pass
        await _send_callback(req.callback_url, result)


async def _send_callback(callback_url: str | None, result: AuditResult):
    if not callback_url:
        return
    try:
        async with httpx.AsyncClient(timeout=settings.callback_timeout_secs) as client:
            resp = await client.post(callback_url, json=result.model_dump(), headers={"X-Worker-Key": settings.worker_api_key})
            logger.info("Callback: %d", resp.status_code)
    except Exception as e:
        logger.error("Callback failed: %s", e)
