import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import AlertConfig, AlertHistory
from app.schemas.alert import (
    AlertConfigCreate,
    AlertConfigResponse,
    AlertConfigUpdate,
    AlertHistoryResponse,
)

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertConfigResponse])
async def list_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertConfig).order_by(AlertConfig.created_at.desc()))
    return [AlertConfigResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/alerts", response_model=AlertConfigResponse, status_code=201)
async def create_alert(data: AlertConfigCreate, db: AsyncSession = Depends(get_db)):
    alert = AlertConfig(**data.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return AlertConfigResponse.model_validate(alert)


@router.patch("/alerts/{alert_id}", response_model=AlertConfigResponse)
async def update_alert(
    alert_id: uuid.UUID,
    data: AlertConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertConfig).where(AlertConfig.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert config not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)

    await db.commit()
    await db.refresh(alert)
    return AlertConfigResponse.model_validate(alert)


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(alert_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertConfig).where(AlertConfig.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert config not found")
    await db.delete(alert)
    await db.commit()


@router.post("/alerts/{alert_id}/test")
async def test_alert(alert_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertConfig).where(AlertConfig.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert config not found")
    # TODO: Send test alert
    return {"status": "test alert would be sent", "config": alert.name}


@router.get("/alerts/history", response_model=list[AlertHistoryResponse])
async def list_alert_history(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertHistory).order_by(AlertHistory.sent_at.desc()).limit(limit)
    )
    return [AlertHistoryResponse.model_validate(h) for h in result.scalars().all()]
