"""Ingestion orchestrator — polls registries, detects new versions, triggers analysis."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.package import Package, Registry
from app.models.version import Version
from app.services.analysis.pipeline import run_analysis_pipeline
from app.services.diff.generator import generate_diff
from app.services.registry import GitHubClient, NpmClient, PyPIClient

logger = logging.getLogger(__name__)

POLL_INTERVALS = {
    "critical": settings.poll_interval_critical,
    "high": settings.poll_interval_high,
    "medium": settings.poll_interval_medium,
    "low": settings.poll_interval_low,
}

REGISTRY_CLIENTS = {
    "npm": NpmClient,
    "pypi": PyPIClient,
    "github": GitHubClient,
}

# Semaphore per registry to limit concurrent requests
REGISTRY_SEMAPHORES = {
    "npm": asyncio.Semaphore(10),
    "pypi": asyncio.Semaphore(10),
    "github": asyncio.Semaphore(5),
}


async def poll_all_packages(db: AsyncSession) -> dict:
    """Poll all enabled packages that are due for a check."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Package).where(Package.monitoring_enabled == True)  # noqa: E712
    )
    packages = result.scalars().all()

    # Snapshot package data before we leave this session
    pkg_data = [
        {
            "id": str(pkg.id),
            "name": pkg.name,
            "registry": pkg.registry,
            "priority": pkg.priority,
            "latest_known_version": pkg.latest_known_version,
            "last_checked_at": pkg.last_checked_at,
            "weekly_downloads": pkg.weekly_downloads,
        }
        for pkg in packages
    ]

    # Filter to packages that are due for a check
    due = []
    for p in pkg_data:
        interval = POLL_INTERVALS.get(p["priority"], 300)
        if p["last_checked_at"] is None:
            due.append(p)
        elif (now - p["last_checked_at"]).total_seconds() >= interval:
            due.append(p)

    logger.info("Polling %d/%d packages (due for check)", len(due), len(pkg_data))

    # Each check gets its own DB session
    tasks = [_check_package_standalone(p) for p in due]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    new_versions = []
    errors = []
    for pkg, res in zip(due, results):
        if isinstance(res, Exception):
            errors.append({"package": pkg["name"], "error": str(res)})
            logger.error("Failed to check %s: %s", pkg["name"], res)
        elif res is not None:
            new_versions.append(res)

    return {
        "checked": len(due),
        "new_versions": len(new_versions),
        "errors": len(errors),
        "details": {
            "new": [
                {"package": v["package"], "version": v["version"]}
                for v in new_versions
            ],
            "errors": errors[:10],
        },
    }


async def _check_package_standalone(pkg_data: dict) -> dict | None:
    """Check a single package with its own DB session."""
    sem = REGISTRY_SEMAPHORES.get(pkg_data["registry"], asyncio.Semaphore(10))

    async with sem:
        async with async_session() as db:
            try:
                result = await _check_package(db, pkg_data)
                await db.commit()
                return result
            except Exception:
                await db.rollback()
                raise


async def _check_package(db: AsyncSession, pkg_data: dict) -> dict | None:
    """Check a single package for new versions."""
    pkg_id = pkg_data["id"]
    pkg_name = pkg_data["name"]
    registry = pkg_data["registry"]
    old_version = pkg_data["latest_known_version"]

    client_cls = REGISTRY_CLIENTS.get(registry)
    if not client_cls:
        raise ValueError(f"Unknown registry: {registry}")

    client = client_cls()
    latest = await client.get_latest_version(pkg_name)

    # Update last_checked_at
    await db.execute(
        update(Package)
        .where(Package.id == pkg_id)
        .values(last_checked_at=datetime.now(timezone.utc))
    )

    if latest.version == old_version:
        return None

    new_version = latest.version
    logger.info("New version detected: %s %s → %s", pkg_name, old_version or "(none)", new_version)

    # Update latest known version
    await db.execute(
        update(Package)
        .where(Package.id == pkg_id)
        .values(latest_known_version=new_version)
    )

    # Generate diff if we have a previous version
    diff_content = ""
    diff_size = 0
    diff_file_count = 0

    if old_version:
        try:
            diff_content, diff_size, diff_file_count = await generate_diff(
                registry=registry,
                package_name=pkg_name,
                old_version=old_version,
                new_version=new_version,
            )
        except Exception as e:
            logger.error("Diff generation failed for %s %s→%s: %s", pkg_name, old_version, new_version, e)

    # Create version record
    version = Version(
        package_id=pkg_id,
        version_string=new_version,
        previous_version_string=old_version,
        published_at=latest.published_at,
        tarball_url=latest.tarball_url,
        sha256_digest=latest.sha256_digest,
        diff_content=diff_content if diff_content else None,
        diff_size_bytes=diff_size,
        diff_file_count=diff_file_count,
    )
    db.add(version)
    await db.flush()

    # Trigger analysis pipeline if we have a diff
    if diff_content:
        try:
            await run_analysis_pipeline(db, str(version.id))
        except Exception as e:
            logger.error("Analysis pipeline failed for %s@%s: %s", pkg_name, new_version, e)

    return {
        "package": pkg_name,
        "version": new_version,
        "previous": old_version,
        "diff_size": diff_size,
        "diff_files": diff_file_count,
    }


async def poll_registry(db: AsyncSession, registry: str) -> dict:
    """Poll only packages from a specific registry."""
    result = await db.execute(
        select(Package).where(
            Package.monitoring_enabled == True,  # noqa: E712
            Package.registry == registry,
        )
    )
    packages = result.scalars().all()

    pkg_data = [
        {
            "id": str(pkg.id),
            "name": pkg.name,
            "registry": pkg.registry,
            "priority": pkg.priority,
            "latest_known_version": pkg.latest_known_version,
            "last_checked_at": pkg.last_checked_at,
            "weekly_downloads": pkg.weekly_downloads,
        }
        for pkg in packages
    ]

    tasks = [_check_package_standalone(p) for p in pkg_data]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    new_versions = [r for r in results if r is not None and not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]

    return {
        "registry": registry,
        "checked": len(packages),
        "new_versions": len(new_versions),
        "errors": len(errors),
    }
