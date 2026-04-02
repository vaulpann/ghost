"""Analysis pipeline — runs the Ghost security agent on detected version updates."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.finding import Finding
from app.models.package import Package
from app.models.version import Version
from app.services.alerting import dispatch_alerts
from app.services.analysis.agent import run_agent_analysis

logger = logging.getLogger(__name__)


async def run_analysis_pipeline(
    db: AsyncSession,
    version_id: str,
) -> Analysis:
    """Run the Ghost security agent on a detected version update."""
    result = await db.execute(select(Version).where(Version.id == version_id))
    version = result.scalar_one()

    result = await db.execute(select(Package).where(Package.id == version.package_id))
    package = result.scalar_one()

    result = await db.execute(select(Analysis).where(Analysis.version_id == version_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        analysis = Analysis(version_id=version_id)
        db.add(analysis)
        await db.flush()

    analysis.status = "in_progress"
    analysis.started_at = datetime.now(timezone.utc)
    await db.flush()

    diff_content = version.diff_content or ""

    if not diff_content:
        analysis.status = "skipped"
        analysis.risk_level = "none"
        analysis.risk_score = 0.0
        analysis.summary = "No diff content available — skipped analysis."
        analysis.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return analysis

    try:
        agent_result, metadata = await run_agent_analysis(
            package_name=package.name,
            registry=package.registry,
            old_version=version.previous_version_string or "unknown",
            new_version=version.version_string,
            diff_content=diff_content,
            weekly_downloads=package.weekly_downloads,
        )

        # Store results
        analysis.risk_score = agent_result.risk_score
        analysis.risk_level = agent_result.risk_level
        analysis.summary = agent_result.summary
        analysis.synthesis_result = {
            "detailed_report": agent_result.detailed_report,
            "recommended_action": agent_result.recommended_action,
        }
        analysis.triage_flagged = agent_result.risk_score >= 2.5
        analysis.triage_model = metadata.get("model", "gpt-4o")
        analysis.status = "complete"
        analysis.completed_at = datetime.now(timezone.utc)

        # Persist findings
        for f in agent_result.findings:
            finding = Finding(
                analysis_id=analysis.id,
                category=f.category,
                severity=f.severity,
                title=f.title,
                description=f.description,
                confidence=f.confidence,
            )
            db.add(finding)

        await db.commit()

        logger.info(
            "Agent analysis complete for %s@%s: risk=%.1f (%s), findings=%d",
            package.name,
            version.version_string,
            analysis.risk_score,
            analysis.risk_level,
            len(agent_result.findings),
        )

        # Dispatch alerts
        try:
            sent = await dispatch_alerts(db, analysis)
            if sent:
                logger.info("Dispatched %d alert(s) for %s@%s", sent, package.name, version.version_string)
        except Exception as e:
            logger.error("Alert dispatch failed for %s@%s: %s", package.name, version.version_string, e)

        return analysis

    except Exception as e:
        logger.error("Agent analysis failed for %s@%s: %s", package.name, version.version_string, e)
        analysis.status = "failed"
        analysis.error_message = str(e)
        analysis.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise
