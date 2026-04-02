"""Seed script: wipe all data, insert 100 packages, fetch metadata from registries."""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session, engine
from app.models.package import Package
from app.services.registry.npm import NpmClient
from app.services.registry.pypi import PyPIClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

NPM_PACKAGES = [
    "lodash", "chalk", "request", "commander", "express",
    "react", "debug", "async", "axios", "fs-extra",
    "moment", "prop-types", "react-dom", "bluebird", "tslib",
    "underscore", "vue", "mkdirp", "glob", "yargs",
    "colors", "inquirer", "webpack", "uuid", "classnames",
    "minimist", "body-parser", "rxjs", "core-js", "typescript",
    "babel-core", "semver", "cheerio", "rimraf", "q",
    "eslint", "dotenv", "js-yaml", "mongoose", "socket.io",
    "ramda", "cors", "prettier", "winston", "jsonwebtoken",
    "nodemon", "ejs", "vite", "tailwindcss", "bcryptjs",
]

PYPI_PACKAGES = [
    "boto3", "urllib3", "requests", "botocore", "setuptools",
    "certifi", "idna", "charset-normalizer", "s3transfer", "typing_extensions",
    "six", "python-dateutil", "pyyaml", "wheel", "pip",
    "cryptography", "rsa", "pyasn1", "jmespath", "colorama",
    "packaging", "attrs", "pytest", "cffi", "werkzeug",
    "flask", "django", "click", "jinja2", "markupsafe",
    "sqlalchemy", "pydantic", "fastapi", "numpy", "pandas",
    "scipy", "scikit-learn", "matplotlib", "seaborn", "tensorflow",
    "torch", "beautifulsoup4", "lxml", "pillow", "aiohttp",
    "pyjwt", "openpyxl", "greenlet", "pytest-cov", "coverage",
]

# Top packages get critical priority, rest get high
NPM_CRITICAL = {"react", "express", "axios", "typescript", "vue", "lodash", "webpack", "vite", "tailwindcss", "eslint"}
PYPI_CRITICAL = {"requests", "boto3", "numpy", "pandas", "django", "flask", "fastapi", "cryptography", "torch", "tensorflow"}


async def wipe_all(db: AsyncSession):
    """Delete all data from all tables."""
    logger.info("Wiping all existing data...")
    await db.execute(text("DELETE FROM alert_history"))
    await db.execute(text("DELETE FROM alert_configs"))
    await db.execute(text("DELETE FROM findings"))
    await db.execute(text("DELETE FROM analyses"))
    await db.execute(text("DELETE FROM versions"))
    await db.execute(text("DELETE FROM packages"))
    await db.commit()
    logger.info("All data wiped.")


async def seed_npm(db: AsyncSession):
    """Seed npm packages with metadata from the registry."""
    client = NpmClient()
    sem = asyncio.Semaphore(5)

    async def fetch_and_insert(name: str):
        async with sem:
            try:
                metadata = await client.get_package_metadata(name)
                latest = await client.get_latest_version(name)
                priority = "critical" if name in NPM_CRITICAL else "high"

                pkg = Package(
                    name=name,
                    registry="npm",
                    registry_url=f"https://www.npmjs.com/package/{name}",
                    repository_url=metadata.repository_url,
                    description=metadata.description,
                    latest_known_version=latest.version,
                    monitoring_enabled=True,
                    priority=priority,
                    weekly_downloads=metadata.weekly_downloads,
                )
                db.add(pkg)
                logger.info("  npm %-25s %10s  %s downloads  [%s]", name, latest.version, f"{metadata.weekly_downloads:,}" if metadata.weekly_downloads else "?", priority)
            except Exception as e:
                logger.error("  npm %-25s FAILED: %s", name, e)

    logger.info("Seeding %d npm packages...", len(NPM_PACKAGES))
    tasks = [fetch_and_insert(name) for name in NPM_PACKAGES]
    await asyncio.gather(*tasks)
    await db.commit()


async def seed_pypi(db: AsyncSession):
    """Seed PyPI packages with metadata from the registry."""
    client = PyPIClient()
    sem = asyncio.Semaphore(5)

    async def fetch_and_insert(name: str):
        async with sem:
            try:
                metadata = await client.get_package_metadata(name)
                latest = await client.get_latest_version(name)
                priority = "critical" if name in PYPI_CRITICAL else "high"

                pkg = Package(
                    name=name,
                    registry="pypi",
                    registry_url=f"https://pypi.org/project/{name}/",
                    repository_url=metadata.repository_url,
                    description=metadata.description,
                    latest_known_version=latest.version,
                    monitoring_enabled=True,
                    priority=priority,
                    weekly_downloads=metadata.weekly_downloads,
                )
                db.add(pkg)
                logger.info("  pypi %-25s %10s  [%s]", name, latest.version, priority)
            except Exception as e:
                logger.error("  pypi %-25s FAILED: %s", name, e)

    logger.info("Seeding %d PyPI packages...", len(PYPI_PACKAGES))
    tasks = [fetch_and_insert(name) for name in PYPI_PACKAGES]
    await asyncio.gather(*tasks)
    await db.commit()


async def main():
    logger.info("=== Ghost Seed Script ===")
    async with async_session() as db:
        await wipe_all(db)
        await seed_npm(db)
        await seed_pypi(db)

    # Verify
    async with async_session() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM packages"))
        count = result.scalar()
        result2 = await db.execute(text("SELECT COUNT(*) FROM packages WHERE latest_known_version IS NOT NULL"))
        with_version = result2.scalar()
        logger.info("=== Done: %d packages seeded, %d with versions ===", count, with_version)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
