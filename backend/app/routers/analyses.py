import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.analysis import Analysis, AnalysisStatus, RiskLevel
from app.models.finding import Finding
from app.models.package import Package, Registry
from app.models.version import Version
from app.schemas.analysis import (
    AnalysisListResponse,
    AnalysisResponse,
    FeedItem,
    FeedResponse,
    StatsResponse,
)

router = APIRouter(tags=["analyses"])


@router.get("/analyses", response_model=AnalysisListResponse)
async def list_analyses(
    status: AnalysisStatus | None = None,
    risk_level: RiskLevel | None = None,
    registry: Registry | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Analysis)
        .join(Version, Analysis.version_id == Version.id)
        .join(Package, Version.package_id == Package.id)
    )
    count_query = (
        select(func.count(Analysis.id))
        .join(Version, Analysis.version_id == Version.id)
        .join(Package, Version.package_id == Package.id)
    )

    if status:
        query = query.where(Analysis.status == status)
        count_query = count_query.where(Analysis.status == status)
    if risk_level:
        query = query.where(Analysis.risk_level == risk_level)
        count_query = count_query.where(Analysis.risk_level == risk_level)
    if registry:
        query = query.where(Package.registry == registry)
        count_query = count_query.where(Package.registry == registry)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        query.options(selectinload(Analysis.findings))
        .order_by(Analysis.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    analyses = result.scalars().all()

    items = []
    for a in analyses:
        # Load related version and package
        v_result = await db.execute(select(Version).where(Version.id == a.version_id))
        version = v_result.scalar_one()
        p_result = await db.execute(select(Package).where(Package.id == version.package_id))
        package = p_result.scalar_one()

        resp = AnalysisResponse.model_validate(a)
        resp.package_name = package.name
        resp.package_registry = package.registry
        resp.version_string = version.version_string
        resp.previous_version_string = version.previous_version_string
        resp.finding_count = len(a.findings) if a.findings else 0
        items.append(resp)

    return AnalysisListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(selectinload(Analysis.findings))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(404, "Analysis not found")

    v_result = await db.execute(select(Version).where(Version.id == analysis.version_id))
    version = v_result.scalar_one()
    p_result = await db.execute(select(Package).where(Package.id == version.package_id))
    package = p_result.scalar_one()

    resp = AnalysisResponse.model_validate(analysis)
    resp.package_name = package.name
    resp.package_registry = package.registry
    resp.version_string = version.version_string
    resp.previous_version_string = version.previous_version_string
    resp.finding_count = len(analysis.findings) if analysis.findings else 0
    return resp


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .where(Analysis.status == AnalysisStatus.COMPLETE)
        .options(selectinload(Analysis.findings))
        .order_by(Analysis.completed_at.desc())
        .limit(limit)
    )
    analyses = result.scalars().all()

    items = []
    for a in analyses:
        v_result = await db.execute(select(Version).where(Version.id == a.version_id))
        version = v_result.scalar_one()
        p_result = await db.execute(select(Package).where(Package.id == version.package_id))
        package = p_result.scalar_one()

        items.append(
            FeedItem(
                id=a.id,
                type="analysis",
                package_name=package.name,
                package_registry=package.registry,
                version_string=version.version_string,
                risk_level=a.risk_level,
                risk_score=a.risk_score,
                summary=a.summary,
                finding_count=len(a.findings) if a.findings else 0,
                created_at=a.completed_at or a.created_at,
            )
        )

    return FeedResponse(items=items)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_packages = (await db.execute(select(func.count(Package.id)))).scalar() or 0
    total_analyses = (await db.execute(select(func.count(Analysis.id)))).scalar() or 0

    analyses_today = (
        await db.execute(
            select(func.count(Analysis.id)).where(Analysis.created_at >= today_start)
        )
    ).scalar() or 0

    flagged_count = (
        await db.execute(
            select(func.count(Analysis.id)).where(Analysis.triage_flagged == True)  # noqa: E712
        )
    ).scalar() or 0

    critical_count = (
        await db.execute(
            select(func.count(Analysis.id)).where(
                Analysis.risk_level.in_(["high", "critical"])
            )
        )
    ).scalar() or 0

    avg_risk = (
        await db.execute(
            select(func.avg(Analysis.risk_score)).where(Analysis.risk_score.isnot(None))
        )
    ).scalar()

    total_findings = (await db.execute(select(func.count(Finding.id)))).scalar() or 0

    return StatsResponse(
        total_packages=total_packages,
        total_analyses=total_analyses,
        analyses_today=analyses_today,
        flagged_count=flagged_count,
        critical_count=critical_count,
        avg_risk_score=round(avg_risk, 2) if avg_risk else None,
        total_findings=total_findings,
    )
