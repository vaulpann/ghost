import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse, FindingUpdate

router = APIRouter(tags=["findings"])


@router.get("/analyses/{analysis_id}/findings", response_model=list[FindingResponse])
async def list_findings(analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Finding)
        .where(Finding.analysis_id == analysis_id)
        .order_by(Finding.severity.desc(), Finding.confidence.desc())
    )
    return [FindingResponse.model_validate(f) for f in result.scalars().all()]


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: uuid.UUID,
    data: FindingUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(404, "Finding not found")

    finding.false_positive = data.false_positive
    await db.commit()
    await db.refresh(finding)
    return FindingResponse.model_validate(finding)
