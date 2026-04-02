import logging

from app.config import settings
from app.services.analysis.models import TriageResult
from app.services.analysis.prompts.triage import (
    TRIAGE_SYSTEM_PROMPT,
    TRIAGE_USER_PROMPT_TEMPLATE,
)
from app.utils.diff_utils import truncate_diff_for_triage
from app.utils.llm import call_llm_structured, estimate_cost

logger = logging.getLogger(__name__)


async def run_triage(
    package_name: str,
    registry: str,
    old_version: str,
    new_version: str,
    diff_content: str,
    diff_file_count: int,
    diff_size_bytes: int,
    dependency_context: str = "",
) -> tuple[TriageResult, dict]:
    """Run Pass 1: Triage analysis using GPT-4o-mini."""
    truncated_diff = truncate_diff_for_triage(diff_content)

    user_prompt = TRIAGE_USER_PROMPT_TEMPLATE.format(
        package_name=package_name,
        registry=registry,
        old_version=old_version,
        new_version=new_version,
        file_count=diff_file_count,
        diff_size=diff_size_bytes,
        diff_content=truncated_diff,
        dependency_context=dependency_context,
    )

    result, meta = await call_llm_structured(
        model=settings.triage_model,
        system_prompt=TRIAGE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=TriageResult,
        temperature=0.0,
        timeout=30.0,
    )

    cost = estimate_cost(settings.triage_model, meta.prompt_tokens, meta.completion_tokens)

    logger.info(
        "Triage complete for %s: verdict=%s, confidence=%.2f, signals=%s",
        package_name,
        result.verdict,
        result.confidence,
        result.signals,
    )

    metadata = {
        "model": meta.model,
        "tokens_used": meta.total_tokens,
        "prompt_tokens": meta.prompt_tokens,
        "completion_tokens": meta.completion_tokens,
        "cost_usd": cost,
    }

    return result, metadata
