import logging

from app.config import settings
from app.services.analysis.models import DeepAnalysisResult, SynthesisResult
from app.services.analysis.prompts.synthesis import (
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_USER_PROMPT_TEMPLATE,
)
from app.utils.llm import call_llm_structured, estimate_cost

logger = logging.getLogger(__name__)


async def run_synthesis(
    package_name: str,
    registry: str,
    old_version: str,
    new_version: str,
    weekly_downloads: int | None,
    deep_result: DeepAnalysisResult,
) -> tuple[SynthesisResult, dict]:
    """Run Pass 3: Synthesis — produce final risk score and report.

    Returns (result, metadata).
    """
    # Format findings for the prompt
    findings_summary_parts = []
    for i, f in enumerate(deep_result.findings, 1):
        evidence_str = ""
        if f.evidence:
            snippets = [
                f"  - `{e.file_path}` L{e.line_start}-{e.line_end}: {e.explanation}"
                for e in f.evidence
            ]
            evidence_str = "\n" + "\n".join(snippets)

        findings_summary_parts.append(
            f"### Finding {i}: [{f.severity.upper()}] {f.title}\n"
            f"Category: {f.category} | Confidence: {f.confidence:.0%}\n"
            f"{f.description}{evidence_str}"
        )

    if deep_result.attack_narrative:
        findings_summary_parts.append(
            f"\n### Attack Narrative\n{deep_result.attack_narrative}"
        )

    findings_summary = "\n\n".join(findings_summary_parts) if findings_summary_parts else "No findings from deep analysis."

    user_prompt = SYNTHESIS_USER_PROMPT_TEMPLATE.format(
        package_name=package_name,
        registry=registry,
        old_version=old_version,
        new_version=new_version,
        weekly_downloads=f"{weekly_downloads:,}" if weekly_downloads else "unknown",
        finding_count=len(deep_result.findings),
        findings_summary=findings_summary,
    )

    result, meta = await call_llm_structured(
        model=settings.synthesis_model,
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=SynthesisResult,
        temperature=0.0,
        timeout=60.0,
    )

    cost = estimate_cost(settings.synthesis_model, meta.prompt_tokens, meta.completion_tokens)

    logger.info(
        "Synthesis complete for %s: risk_score=%.1f, risk_level=%s, action=%s",
        package_name,
        result.risk_score,
        result.risk_level,
        result.recommended_action,
    )

    metadata = {
        "model": meta.model,
        "tokens_used": meta.total_tokens,
        "prompt_tokens": meta.prompt_tokens,
        "completion_tokens": meta.completion_tokens,
        "cost_usd": cost,
    }

    return result, metadata
