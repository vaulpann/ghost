"""Webhook endpoints — protected by admin API key."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.ingestion import poll_all_packages, poll_registry

router = APIRouter(tags=["webhooks"])


def _verify_admin_key(x_api_key: str = Header(default=""), authorization: str = Header(default="")):
    """Check admin API key from header or Cloud Scheduler's User-Agent."""
    if not settings.admin_api_key:
        return  # No key configured = allow (dev mode)
    # Accept via X-API-Key header
    if x_api_key == settings.admin_api_key:
        return
    # Accept via Bearer token
    if authorization.replace("Bearer ", "") == settings.admin_api_key:
        return
    # Allow Cloud Scheduler (uses OIDC, identified by User-Agent)
    # In production, replace this with proper OIDC verification
    raise HTTPException(403, "Invalid API key")


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
