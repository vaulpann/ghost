import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.package import Package
from app.schemas.package import (
    PackageListResponse,
    PackageResponse,
)

router = APIRouter(tags=["packages"])


@router.get("/packages", response_model=PackageListResponse)
async def list_packages(
    registry: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Package)
    count_query = select(func.count(Package.id))

    if registry:
        query = query.where(Package.registry == registry)
        count_query = count_query.where(Package.registry == registry)
    if priority:
        query = query.where(Package.priority == priority)
        count_query = count_query.where(Package.priority == priority)
    if search:
        query = query.where(Package.name.ilike(f"%{search}%"))
        count_query = count_query.where(Package.name.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(Package.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    return PackageListResponse(
        items=[PackageResponse.model_validate(p) for p in result.scalars().all()],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/packages/{package_id}", response_model=PackageResponse)
async def get_package(package_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(404, "Package not found")
    return PackageResponse.model_validate(package)
