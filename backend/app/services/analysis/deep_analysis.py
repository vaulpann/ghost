import logging

from app.config import settings
from app.services.analysis.models import DeepAnalysisResult
from app.services.analysis.prompts.deep_analysis import (
    DEEP_ANALYSIS_SYSTEM_PROMPT,
    DEEP_ANALYSIS_USER_PROMPT_TEMPLATE,
)
from app.utils.llm import call_llm_structured, estimate_cost

logger = logging.getLogger(__name__)


async def run_deep_analysis(
    package_name: str,
    registry: str,
    old_version: str,
    new_version: str,
    diff_content: str,
    triage_signals: list[str],
    triage_reasoning: str,
    dependency_context: str = "",
) -> tuple[DeepAnalysisResult, dict]:
    """Run Pass 2: Deep semantic analysis using GPT-4o."""
    user_prompt = DEEP_ANALYSIS_USER_PROMPT_TEMPLATE.format(
        package_name=package_name,
        registry=registry,
        old_version=old_version,
        new_version=new_version,
        triage_signals=", ".join(triage_signals) if triage_signals else "none specified",
        triage_reasoning=triage_reasoning,
        diff_content=diff_content,
        dependency_context=dependency_context,
    )

    result, meta = await call_llm_structured(
        model=settings.deep_analysis_model,
        system_prompt=DEEP_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=DeepAnalysisResult,
        temperature=0.0,
        timeout=120.0,
    )

    cost = estimate_cost(
        settings.deep_analysis_model, meta.prompt_tokens, meta.completion_tokens
    )

    logger.info(
        "Deep analysis complete for %s: %d findings, attack_narrative=%s",
        package_name,
        len(result.findings),
        bool(result.attack_narrative),
    )

    metadata = {
        "model": meta.model,
        "tokens_used": meta.total_tokens,
        "prompt_tokens": meta.prompt_tokens,
        "completion_tokens": meta.completion_tokens,
        "cost_usd": cost,
    }

    return result, metadata
