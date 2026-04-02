import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse

router = APIRouter(tags=["findings"])


@router.get("/analyses/{analysis_id}/findings", response_model=list[FindingResponse])
async def list_findings(analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Finding)
        .where(Finding.analysis_id == analysis_id)
        .order_by(Finding.created_at.desc())
    )
    return [FindingResponse.model_validate(f) for f in result.scalars().all()]
