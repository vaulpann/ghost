"""Analysis pipeline orchestrator — chains dependency investigation → triage → deep analysis → synthesis."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.finding import Finding
from app.models.package import Package
from app.models.version import Version
from app.services.alerting import dispatch_alerts
from app.services.analysis.deep_analysis import run_deep_analysis
from app.services.analysis.dependency_analysis import (
    extract_new_dependencies,
    investigate_dependencies,
)
from app.services.analysis.synthesis import run_synthesis
from app.services.analysis.triage import run_triage

logger = logging.getLogger(__name__)


async def run_analysis_pipeline(
    db: AsyncSession,
    version_id: str,
) -> Analysis:
    """Run the full analysis pipeline for a detected version update.

    0. Dependency investigation — detect new deps, download and scan their source
    1. Triage (GPT-4o-mini) — flag or skip, with dependency context
    2. Deep Analysis (GPT-4o) — extract findings, with dependency context
    3. Synthesis (GPT-4o) — risk score + report
    """
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

    analysis.status = "triage_in_progress"
    analysis.started_at = datetime.now(timezone.utc)
    await db.flush()

    total_cost = 0.0
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
        # === PASS 0: DEPENDENCY INVESTIGATION ===
        dependency_context = ""
        dep_investigation_results = []

        new_deps = extract_new_dependencies(diff_content, package.registry)
        if new_deps:
            logger.info(
                "Found %d new dependencies in %s@%s: %s",
                len(new_deps),
                package.name,
                version.version_string,
                [d["name"] for d in new_deps],
            )
            dep_investigation_results = await investigate_dependencies(new_deps, package.registry)

            # Build context string for LLM prompts
            dep_parts = ["## New Dependency Investigation Results\n"]
            for dep_info in dep_investigation_results:
                dep_parts.append(dep_info.to_prompt_text())
            dependency_context = "\n\n".join(dep_parts)

            logger.info(
                "Dependency investigation complete: %d deps analyzed, %d with suspicious files",
                len(dep_investigation_results),
                sum(1 for d in dep_investigation_results if d.suspicious_files),
            )
        else:
            dependency_context = "## New Dependencies: None detected in this update."

        # === PASS 1: TRIAGE ===
        triage_result, triage_meta = await run_triage(
            package_name=package.name,
            registry=package.registry,
            old_version=version.previous_version_string or "unknown",
            new_version=version.version_string,
            diff_content=diff_content,
            diff_file_count=version.diff_file_count or 0,
            diff_size_bytes=version.diff_size_bytes or 0,
            dependency_context=dependency_context,
        )

        analysis.triage_result = triage_result.model_dump()
        analysis.triage_flagged = triage_result.verdict.upper() == "SUSPICIOUS"
        analysis.triage_model = triage_meta["model"]
        analysis.triage_tokens_used = triage_meta["tokens_used"]
        analysis.triage_completed_at = datetime.now(timezone.utc)
        analysis.status = "triage_complete"
        total_cost += triage_meta["cost_usd"]
        await db.flush()

        # If triage says BENIGN, skip deep analysis
        if not analysis.triage_flagged:
            analysis.status = "complete"
            analysis.risk_score = 0.0
            analysis.risk_level = "none"
            analysis.summary = f"Triage passed — no suspicious signals detected. {triage_result.reasoning}"
            analysis.total_cost_usd = total_cost
            analysis.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Analysis complete (benign) for %s@%s", package.name, version.version_string)

            try:
                await dispatch_alerts(db, analysis)
            except Exception as e:
                logger.error("Alert dispatch failed: %s", e)

            return analysis

        # === PASS 2: DEEP ANALYSIS ===
        analysis.status = "deep_analysis_in_progress"
        await db.flush()

        deep_result, deep_meta = await run_deep_analysis(
            package_name=package.name,
            registry=package.registry,
            old_version=version.previous_version_string or "unknown",
            new_version=version.version_string,
            diff_content=diff_content,
            triage_signals=triage_result.signals,
            triage_reasoning=triage_result.reasoning,
            dependency_context=dependency_context,
        )

        analysis.deep_analysis_result = deep_result.model_dump()
        analysis.deep_analysis_model = deep_meta["model"]
        analysis.deep_analysis_tokens_used = deep_meta["tokens_used"]
        analysis.deep_analysis_completed_at = datetime.now(timezone.utc)
        analysis.status = "deep_analysis_complete"
        total_cost += deep_meta["cost_usd"]
        await db.flush()

        # Persist findings
        for f in deep_result.findings:
            finding = Finding(
                analysis_id=analysis.id,
                category=f.category,
                severity=f.severity.lower(),
                title=f.title,
                description=f.description,
                evidence={
                    "items": [e.model_dump() for e in f.evidence]
                } if f.evidence else None,
                confidence=f.confidence,
                mitre_technique=f.mitre_technique,
                remediation=f.remediation,
            )
            db.add(finding)
        await db.flush()

        # === PASS 3: SYNTHESIS ===
        analysis.status = "synthesis_in_progress"
        await db.flush()

        synth_result, synth_meta = await run_synthesis(
            package_name=package.name,
            registry=package.registry,
            old_version=version.previous_version_string or "unknown",
            new_version=version.version_string,
            weekly_downloads=package.weekly_downloads,
            deep_result=deep_result,
        )

        analysis.synthesis_result = synth_result.model_dump()
        analysis.risk_score = synth_result.risk_score
        analysis.risk_level = synth_result.risk_level.lower()
        analysis.summary = synth_result.summary
        analysis.status = "complete"
        total_cost += synth_meta["cost_usd"]
        analysis.total_cost_usd = total_cost
        analysis.completed_at = datetime.now(timezone.utc)

        await db.commit()

        logger.info(
            "Analysis complete for %s@%s: risk=%.1f (%s), findings=%d, cost=$%.4f",
            package.name,
            version.version_string,
            analysis.risk_score,
            analysis.risk_level,
            len(deep_result.findings),
            total_cost,
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
        logger.error("Analysis pipeline failed for %s@%s: %s", package.name, version.version_string, e)
        analysis.status = "failed"
        analysis.error_message = str(e)
        analysis.total_cost_usd = total_cost
        analysis.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise
