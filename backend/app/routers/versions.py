import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import Analysis
from app.models.version import Version
from app.schemas.version import VersionListResponse, VersionResponse
from app.services.analysis.pipeline import run_analysis_pipeline

router = APIRouter(tags=["versions"])


@router.get("/packages/{package_id}/versions", response_model=VersionListResponse)
async def list_versions(
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    count = (
        await db.execute(
            select(func.count(Version.id)).where(Version.package_id == package_id)
        )
    ).scalar() or 0

    result = await db.execute(
        select(Version)
        .where(Version.package_id == package_id)
        .order_by(Version.created_at.desc())
    )
    versions = result.scalars().all()

    items = []
    for v in versions:
        resp = VersionResponse.model_validate(v)
        # Enrich with analysis info
        analysis_result = await db.execute(
            select(Analysis).where(Analysis.version_id == v.id)
        )
        analysis = analysis_result.scalar_one_or_none()
        if analysis:
            resp.has_analysis = True
            resp.risk_level = analysis.risk_level
            resp.risk_score = analysis.risk_score
        items.append(resp)

    return VersionListResponse(items=items, total=count)


@router.get("/versions/{version_id}", response_model=VersionResponse)
async def get_version(version_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Version).where(Version.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "Version not found")

    resp = VersionResponse.model_validate(version)
    analysis_result = await db.execute(
        select(Analysis).where(Analysis.version_id == version_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if analysis:
        resp.has_analysis = True
        resp.risk_level = analysis.risk_level
        resp.risk_score = analysis.risk_score

    return resp


@router.get("/versions/{version_id}/diff")
async def get_version_diff(version_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Version).where(Version.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "Version not found")
    return {"diff": version.diff_content or "", "file_count": version.diff_file_count}


@router.post("/versions/{version_id}/reanalyze")
async def reanalyze_version(
    version_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Version).where(Version.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "Version not found")

    if not version.diff_content:
        raise HTTPException(400, "No diff content available for analysis")

    # Delete existing analysis
    existing = await db.execute(
        select(Analysis).where(Analysis.version_id == version_id)
    )
    old_analysis = existing.scalar_one_or_none()
    if old_analysis:
        await db.delete(old_analysis)
        await db.flush()

    analysis = await run_analysis_pipeline(db, str(version_id))
    return {"status": "complete", "analysis_id": str(analysis.id)}
