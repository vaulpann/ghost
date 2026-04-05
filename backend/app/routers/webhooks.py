"""Webhook endpoints — protected by admin API key."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.package import Package
from app.services.audit.pipeline import process_audit_callback, trigger_vulnerability_scan
from app.services.ingestion import poll_all_packages, poll_registry

router = APIRouter(tags=["webhooks"])


def _verify_admin_key(x_api_key: str = Header(default=""), authorization: str = Header(default="")):
    if not settings.admin_api_key:
        return
    if x_api_key == settings.admin_api_key:
        return
    if authorization.replace("Bearer ", "") == settings.admin_api_key:
        return
    raise HTTPException(403, "Invalid API key")


def _verify_worker_key(x_worker_key: str = Header(default="")):
    if not settings.audit_worker_api_key:
        return
    if x_worker_key != settings.audit_worker_api_key:
        raise HTTPException(403, "Invalid worker key")


@router.post("/webhooks/poll")
async def trigger_poll(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    result = await poll_all_packages(db)
    return result


@router.post("/webhooks/poll/{registry}")
async def trigger_poll_registry(
    registry: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    result = await poll_registry(db, registry)
    return result


@router.post("/webhooks/audit/{package_id}")
async def trigger_audit(
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    """Manually trigger a vulnerability scan for a package."""
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(404, "Package not found")
    if not package.latest_known_version:
        raise HTTPException(400, "Package has no known version yet")

    scan = await trigger_vulnerability_scan(
        db, package, package.latest_known_version, trigger="manual"
    )
    return {"scan_id": str(scan.id), "status": scan.status}


@router.post("/webhooks/audit-callback")
async def audit_callback(
    result: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_worker_key),
):
    """Receive results from the audit worker VM."""
    scan = await process_audit_callback(db, result)
    if not scan:
        raise HTTPException(400, "Failed to process callback")
    return {"scan_id": str(scan.id), "status": scan.status}
