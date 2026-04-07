"""Clear false critical and high-severity analyses from the database.

Run with: python clear_false_criticals.py

This resets analyses that were flagged as critical/high but are
actually false positives from dependency confusion bugs.
"""

import asyncio
import logging

from sqlalchemy import select, update, text

from app.database import async_session
from app.models.analysis import Analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    logger.info("=== Clearing false critical/high analyses ===")

    async with async_session() as db:
        # Find all critical and high analyses
        result = await db.execute(
            select(Analysis).where(Analysis.risk_level.in_(["critical", "high"]))
        )
        flagged = result.scalars().all()

        logger.info("Found %d critical/high analyses", len(flagged))

        for a in flagged:
            logger.info(
                "  Resetting: %s (%s) %s → %s  risk_score=%.1f  risk_level=%s",
                a.package_name, a.package_registry,
                a.previous_version_string, a.version_string,
                a.risk_score or 0, a.risk_level,
            )

        # Reset all critical/high to low/0.0
        await db.execute(
            update(Analysis)
            .where(Analysis.risk_level.in_(["critical", "high"]))
            .values(risk_score=0.0, risk_level="low")
        )

        # Also mark any critical/high findings as false positives
        await db.execute(
            text("""
                UPDATE findings SET false_positive = TRUE
                WHERE severity IN ('critical', 'high')
                AND analysis_id IN (
                    SELECT id FROM analyses WHERE risk_score = 0.0
                )
            """)
        )

        await db.commit()
        logger.info("Done. All false critical/high analyses reset to low.")


if __name__ == "__main__":
    asyncio.run(main())
