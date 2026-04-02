import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.analysis import Analysis
from app.models.finding import Finding
from app.models.package import Package
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
    status: str | None = None,
    risk_level: str | None = None,
    registry: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    # Single query with joins — no N+1
    query = (
        select(
            Analysis.id,
            Analysis.version_id,
            Analysis.status,
            Analysis.triage_flagged,
            Analysis.risk_score,
            Analysis.risk_level,
            Analysis.summary,
            Analysis.total_cost_usd,
            Analysis.created_at,
            Analysis.completed_at,
            Package.name.label("package_name"),
            Package.registry.label("package_registry"),
            Version.version_string,
            Version.previous_version_string,
            func.count(Finding.id).label("finding_count"),
        )
        .join(Version, Analysis.version_id == Version.id)
        .join(Package, Version.package_id == Package.id)
        .outerjoin(Finding, Finding.analysis_id == Analysis.id)
        .group_by(Analysis.id, Package.name, Package.registry, Version.version_string, Version.previous_version_string)
    )

    count_query = (
        select(func.count(func.distinct(Analysis.id)))
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
        query.order_by(Analysis.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = result.all()

    items = []
    for row in rows:
        items.append(AnalysisResponse(
            id=row.id,
            version_id=row.version_id,
            status=row.status,
            triage_result=None,
            triage_flagged=row.triage_flagged,
            triage_model=None,
            triage_tokens_used=None,
            triage_completed_at=None,
            deep_analysis_result=None,
            deep_analysis_model=None,
            deep_analysis_tokens_used=None,
            deep_analysis_completed_at=None,
            synthesis_result=None,
            risk_score=row.risk_score,
            risk_level=row.risk_level,
            summary=row.summary,
            error_message=None,
            total_cost_usd=row.total_cost_usd,
            started_at=None,
            completed_at=row.completed_at,
            created_at=row.created_at,
            package_name=row.package_name,
            package_registry=row.package_registry,
            version_string=row.version_string,
            previous_version_string=row.previous_version_string,
            finding_count=row.finding_count,
        ))

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

    # Two extra queries for a single detail page is fine
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
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = (
        await db.execute(
            select(func.count(Analysis.id)).where(Analysis.status == "complete")
        )
    ).scalar() or 0

    result = await db.execute(
        select(
            Analysis.id,
            Analysis.risk_level,
            Analysis.risk_score,
            Analysis.summary,
            Analysis.completed_at,
            Analysis.created_at,
            Package.name.label("package_name"),
            Package.registry.label("package_registry"),
            Version.version_string,
            func.count(Finding.id).label("finding_count"),
        )
        .join(Version, Analysis.version_id == Version.id)
        .join(Package, Version.package_id == Package.id)
        .outerjoin(Finding, Finding.analysis_id == Analysis.id)
        .where(Analysis.status == "complete")
        .group_by(Analysis.id, Package.name, Package.registry, Version.version_string)
        .order_by(Analysis.completed_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = result.all()

    items = [
        FeedItem(
            id=row.id,
            type="analysis",
            package_name=row.package_name,
            package_registry=row.package_registry,
            version_string=row.version_string,
            risk_level=row.risk_level,
            risk_score=row.risk_score,
            summary=row.summary,
            finding_count=row.finding_count,
            created_at=row.completed_at or row.created_at,
        )
        for row in rows
    ]

    return FeedResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Run all count queries in parallel-ish (single round trip each, but fast)
    total_packages = (await db.execute(select(func.count(Package.id)))).scalar() or 0
    total_analyses = (await db.execute(select(func.count(Analysis.id)))).scalar() or 0

    analyses_today = (
        await db.execute(
            select(func.count(Analysis.id)).where(Analysis.created_at >= today_start)
        )
    ).scalar() or 0

    flagged_count = (
        await db.execute(
            select(func.count(Analysis.id)).where(Analysis.risk_score >= 2.5)
        )
    ).scalar() or 0

    critical_count = (
        await db.execute(
            select(func.count(Analysis.id)).where(Analysis.risk_score >= 5.0)
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
