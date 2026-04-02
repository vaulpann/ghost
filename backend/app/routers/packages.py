import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.package import Package, Priority, Registry
from app.schemas.package import (
    PackageCreate,
    PackageListResponse,
    PackageResponse,
    PackageSeedRequest,
    PackageUpdate,
)
from app.services.registry import GitHubClient, NpmClient, PyPIClient

router = APIRouter(tags=["packages"])

TOP_NPM_PACKAGES = [
    "lodash", "chalk", "react", "express", "axios", "tslib", "commander",
    "moment", "debug", "uuid", "fs-extra", "glob", "mkdirp", "minimist",
    "async", "yargs", "semver", "dotenv", "inquirer", "rxjs", "bluebird",
    "underscore", "webpack", "babel-core", "typescript", "eslint", "prettier",
    "request", "body-parser", "cors", "jsonwebtoken", "mongoose", "socket.io",
    "next", "vue", "angular", "svelte", "jquery", "d3", "three",
    "tailwindcss", "postcss", "autoprefixer", "vite", "esbuild", "rollup",
    "jest", "mocha", "chai", "nodemon",
]

TOP_PYPI_PACKAGES = [
    "requests", "boto3", "urllib3", "setuptools", "typing-extensions",
    "botocore", "pip", "certifi", "charset-normalizer", "idna",
    "numpy", "packaging", "pyyaml", "s3transfer", "six",
    "python-dateutil", "cryptography", "jinja2", "markupsafe", "pyasn1",
    "rsa", "colorama", "click", "attrs", "pydantic",
    "pillow", "pandas", "scipy", "matplotlib", "flask",
    "django", "fastapi", "httpx", "aiohttp", "celery",
    "sqlalchemy", "psycopg2-binary", "redis", "pytest", "black",
    "mypy", "ruff", "gunicorn", "uvicorn", "rich",
    "httptools", "orjson", "pyjwt", "paramiko", "fabric",
]


@router.get("/packages", response_model=PackageListResponse)
async def list_packages(
    registry: Registry | None = None,
    priority: Priority | None = None,
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


@router.post("/packages", response_model=PackageResponse, status_code=201)
async def create_package(
    data: PackageCreate,
    db: AsyncSession = Depends(get_db),
):
    # Check for duplicates
    existing = await db.execute(
        select(Package).where(Package.registry == data.registry, Package.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Package {data.name} already monitored on {data.registry}")

    # Fetch metadata from registry
    registry_url = data.registry_url
    if not registry_url:
        match data.registry:
            case Registry.NPM:
                registry_url = f"https://www.npmjs.com/package/{data.name}"
            case Registry.PYPI:
                registry_url = f"https://pypi.org/project/{data.name}/"
            case Registry.GITHUB:
                registry_url = f"https://github.com/{data.name}"

    package = Package(
        name=data.name,
        registry=data.registry,
        registry_url=registry_url,
        repository_url=data.repository_url,
        description=data.description,
        priority=data.priority,
        monitoring_enabled=data.monitoring_enabled,
    )
    db.add(package)
    await db.flush()

    # Try to fetch current version and metadata in background
    try:
        client = _get_client(data.registry)
        metadata = await client.get_package_metadata(data.name)
        package.description = package.description or metadata.description
        package.repository_url = package.repository_url or metadata.repository_url
        package.weekly_downloads = metadata.weekly_downloads

        latest = await client.get_latest_version(data.name)
        package.latest_known_version = latest.version
    except Exception:
        pass  # Non-critical — will be populated on first poll

    await db.commit()
    await db.refresh(package)
    return PackageResponse.model_validate(package)


@router.get("/packages/{package_id}", response_model=PackageResponse)
async def get_package(package_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(404, "Package not found")
    return PackageResponse.model_validate(package)


@router.patch("/packages/{package_id}", response_model=PackageResponse)
async def update_package(
    package_id: uuid.UUID,
    data: PackageUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(404, "Package not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(package, field, value)

    await db.commit()
    await db.refresh(package)
    return PackageResponse.model_validate(package)


@router.delete("/packages/{package_id}", status_code=204)
async def delete_package(package_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(404, "Package not found")
    await db.delete(package)
    await db.commit()


@router.post("/packages/seed")
async def seed_packages(
    data: PackageSeedRequest,
    db: AsyncSession = Depends(get_db),
):
    """Bulk-add top packages for a registry."""
    match data.registry:
        case Registry.NPM:
            package_names = TOP_NPM_PACKAGES[:data.count]
        case Registry.PYPI:
            package_names = TOP_PYPI_PACKAGES[:data.count]
        case _:
            raise HTTPException(400, "Seeding not supported for this registry yet")

    added = 0
    skipped = 0
    for name in package_names:
        existing = await db.execute(
            select(Package).where(Package.registry == data.registry, Package.name == name)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        match data.registry:
            case Registry.NPM:
                url = f"https://www.npmjs.com/package/{name}"
            case Registry.PYPI:
                url = f"https://pypi.org/project/{name}/"
            case _:
                url = None

        package = Package(
            name=name,
            registry=data.registry,
            registry_url=url,
            priority=Priority.HIGH,
            monitoring_enabled=True,
        )
        db.add(package)
        added += 1

    await db.commit()
    return {"added": added, "skipped": skipped, "total": added + skipped}


def _get_client(registry: Registry):
    match registry:
        case Registry.NPM:
            return NpmClient()
        case Registry.PYPI:
            return PyPIClient()
        case Registry.GITHUB:
            return GitHubClient()
