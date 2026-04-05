"""Ghost Audit Worker — Codex-powered vulnerability scanner."""

import asyncio
import json
import logging
import time
import uuid

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException

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
from app.prompts import DISCOVERY_PROMPT, VALIDATION_PROMPT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("ghost-worker")

app = FastAPI(title="Ghost Audit Worker", version="0.1.0")

# Concurrency control
_semaphore = asyncio.Semaphore(settings.max_concurrent_audits)
_audits: dict[str, AuditStatusResponse] = {}
_queue_depth = 0


def _verify_key(x_worker_key: str = Header(default="")):
    if not settings.worker_api_key:
        return
    if x_worker_key != settings.worker_api_key:
        raise HTTPException(403, "Invalid worker key")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ghost-audit-worker",
        "queue_depth": _queue_depth,
        "max_concurrent": settings.max_concurrent_audits,
    }


@app.post("/audit")
async def submit_audit(
    req: AuditRequest,
    background_tasks: BackgroundTasks,
    _: None = None,
):
    """Submit a vulnerability audit. Runs asynchronously."""
    global _queue_depth
    if _queue_depth >= settings.max_queue_depth:
        raise HTTPException(503, "Audit queue full. Try again later.")

    audit_id = req.audit_id or str(uuid.uuid4())
    _audits[audit_id] = AuditStatusResponse(
        audit_id=audit_id, status="accepted"
    )
    _queue_depth += 1

    background_tasks.add_task(_run_audit, audit_id, req)

    return {"audit_id": audit_id, "status": "accepted"}


@app.get("/audit/{audit_id}/status")
async def get_audit_status(audit_id: str):
    if audit_id not in _audits:
        raise HTTPException(404, "Audit not found")
    return _audits[audit_id]


async def _run_audit(audit_id: str, req: AuditRequest):
    """Full two-pass audit: discovery → validation."""
    global _queue_depth
    result = AuditResult(audit_id=audit_id, status="running")

    try:
        async with _semaphore:
            # === DOWNLOAD ===
            _audits[audit_id].status = "downloading"
            source_path, size_bytes, file_count = await download_package_source(
                req.package_name, req.version, req.registry, req.tarball_url
            )
            result.source_size_bytes = size_bytes
            result.source_file_count = file_count

            # === DISCOVERY PASS ===
            _audits[audit_id].status = "discovery"
            _audits[audit_id].progress = f"Scanning {file_count} files..."

            discovery_prompt = DISCOVERY_PROMPT.format(
                package_name=req.package_name,
                registry=req.registry,
                version=req.version,
            )

            discovery_output = await run_codex(
                prompt=discovery_prompt,
                working_dir=source_path,
                model=settings.codex_discovery_model,
                timeout_secs=settings.codex_timeout_secs,
            )

            result.discovery_model = settings.codex_discovery_model
            result.discovery_duration_secs = discovery_output["duration_secs"]

            # Parse discovery results
            discovery_data = parse_json_from_output(discovery_output["stdout"])
            if not discovery_data:
                logger.warning("Codex discovery produced no parseable JSON")
                result.status = "complete"
                result.discovery_findings = []
                await _send_callback(req.callback_url, result)
                return

            findings = []
            for v in discovery_data.get("vulnerabilities", []):
                try:
                    findings.append(DiscoveryFinding(**v))
                except Exception as e:
                    logger.warning("Skipping malformed finding: %s", e)

            result.discovery_findings = findings
            logger.info(
                "Discovery complete: %d findings for %s@%s",
                len(findings), req.package_name, req.version,
            )

            # Skip validation if no findings
            if not findings:
                result.status = "complete"
                await _send_callback(req.callback_url, result)
                return

            # Filter to findings with confidence >= 0.5
            credible_findings = [f for f in findings if f.confidence >= 0.5]
            if not credible_findings:
                result.status = "complete"
                await _send_callback(req.callback_url, result)
                return

            # === VALIDATION PASS ===
            _audits[audit_id].status = "validation"
            _audits[audit_id].progress = f"Validating {len(credible_findings)} findings..."

            discovery_json = json.dumps(
                [f.model_dump() for f in credible_findings], indent=2
            )

            validation_prompt = VALIDATION_PROMPT.format(
                package_name=req.package_name,
                registry=req.registry,
                version=req.version,
                discovery_json=discovery_json,
            )

            validation_output = await run_codex(
                prompt=validation_prompt,
                working_dir=source_path,
                model=settings.codex_validation_model,
                timeout_secs=settings.codex_timeout_secs,
            )

            result.validation_model = settings.codex_validation_model
            result.validation_duration_secs = validation_output["duration_secs"]

            # Parse validation results
            validation_data = parse_json_from_output(validation_output["stdout"])
            if validation_data:
                for v in validation_data.get("validated", []):
                    try:
                        result.validated_vulnerabilities.append(
                            ValidatedVulnerability(**v)
                        )
                    except Exception as e:
                        logger.warning("Skipping malformed validation: %s", e)

                for r in validation_data.get("rejected", []):
                    idx = r.get("original_index")
                    if idx is not None:
                        result.rejected_indices.append(idx)

            logger.info(
                "Validation complete: %d confirmed, %d rejected for %s@%s",
                len(result.validated_vulnerabilities),
                len(result.rejected_indices),
                req.package_name,
                req.version,
            )

            result.status = "complete"

    except Exception as e:
        logger.error("Audit failed for %s@%s: %s", req.package_name, req.version, e)
        result.status = "failed"
        result.error = str(e)

    finally:
        _queue_depth -= 1
        _audits[audit_id] = AuditStatusResponse(
            audit_id=audit_id,
            status=result.status,
            error=result.error,
        )

        # Cleanup source
        try:
            cleanup_source(req.package_name, req.version)
        except Exception:
            pass

        # Send callback
        await _send_callback(req.callback_url, result)


async def _send_callback(callback_url: str | None, result: AuditResult):
    """POST results back to Cloud Run."""
    if not callback_url:
        return

    try:
        async with httpx.AsyncClient(timeout=settings.callback_timeout_secs) as client:
            resp = await client.post(
                callback_url,
                json=result.model_dump(),
                headers={"X-Worker-Key": settings.worker_api_key},
            )
            logger.info("Callback sent to %s: status=%d", callback_url, resp.status_code)
    except Exception as e:
        logger.error("Callback failed: %s", e)
