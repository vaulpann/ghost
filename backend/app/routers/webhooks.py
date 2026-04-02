"""Webhook endpoints for Cloud Scheduler and external triggers."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.package import Registry
from app.services.ingestion import poll_all_packages, poll_registry

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/poll")
async def trigger_poll(db: AsyncSession = Depends(get_db)):
    """Trigger polling for all enabled packages. Called by Cloud Scheduler every minute."""
    result = await poll_all_packages(db)
    return result


@router.post("/webhooks/poll/{registry}")
async def trigger_poll_registry(registry: Registry, db: AsyncSession = Depends(get_db)):
    """Trigger polling for a specific registry."""
    result = await poll_registry(db, registry)
    return result
