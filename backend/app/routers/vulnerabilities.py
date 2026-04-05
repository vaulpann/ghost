import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.package import Package
from app.models.vulnerability import Vulnerability
from app.models.vulnerability_scan import VulnerabilityScan
from app.schemas.vulnerability import VulnerabilityListResponse, VulnerabilityResponse

router = APIRouter(tags=["vulnerabilities"])


@router.get("/vulnerabilities", response_model=VulnerabilityListResponse)
async def list_vulnerabilities(
    severity: str | None = None,
    category: str | None = None,
    package_id: uuid.UUID | None = None,
    validated: bool = True,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            Vulnerability,
            Package.name.label("package_name"),
            Package.registry.label("package_registry"),
            VulnerabilityScan.version_string.label("version_string"),
        )
        .join(Package, Vulnerability.package_id == Package.id)
        .join(VulnerabilityScan, Vulnerability.scan_id == VulnerabilityScan.id)
    )

    count_query = select(func.count(Vulnerability.id))

    if severity:
        query = query.where(Vulnerability.severity == severity)
        count_query = count_query.where(Vulnerability.severity == severity)
    if category:
        query = query.where(Vulnerability.category == category)
        count_query = count_query.where(Vulnerability.category == category)
    if package_id:
        query = query.where(Vulnerability.package_id == package_id)
        count_query = count_query.where(Vulnerability.package_id == package_id)

    query = query.where(Vulnerability.validated == validated)
    count_query = count_query.where(Vulnerability.validated == validated)
    query = query.where(Vulnerability.false_positive == False)  # noqa: E712
    count_query = count_query.where(Vulnerability.false_positive == False)  # noqa: E712

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        query.order_by(Vulnerability.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = result.all()

    items = []
    for row in rows:
        vuln = row[0]  # Vulnerability object
        resp = VulnerabilityResponse.model_validate(vuln)
        resp.package_name = row.package_name
        resp.package_registry = row.package_registry
        resp.version_string = row.version_string
        items.append(resp)

    return VulnerabilityListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/vulnerabilities/{vuln_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(vuln_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Vulnerability).where(Vulnerability.id == vuln_id)
    )
    vuln = result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(404, "Vulnerability not found")

    pkg = await db.execute(select(Package).where(Package.id == vuln.package_id))
    package = pkg.scalar_one()

    scan = await db.execute(
        select(VulnerabilityScan).where(VulnerabilityScan.id == vuln.scan_id)
    )
    scan_obj = scan.scalar_one()

    resp = VulnerabilityResponse.model_validate(vuln)
    resp.package_name = package.name
    resp.package_registry = package.registry
    resp.version_string = scan_obj.version_string
    return resp


@router.get("/packages/{package_id}/vulnerabilities", response_model=list[VulnerabilityResponse])
async def get_package_vulnerabilities(
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Vulnerability)
        .where(
            Vulnerability.package_id == package_id,
            Vulnerability.validated == True,  # noqa: E712
            Vulnerability.false_positive == False,  # noqa: E712
        )
        .order_by(Vulnerability.severity.desc(), Vulnerability.created_at.desc())
    )
    vulns = result.scalars().all()

    pkg = await db.execute(select(Package).where(Package.id == package_id))
    package = pkg.scalar_one_or_none()

    items = []
    for v in vulns:
        resp = VulnerabilityResponse.model_validate(v)
        if package:
            resp.package_name = package.name
            resp.package_registry = package.registry
        items.append(resp)

    return items
