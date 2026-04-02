import logging
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


class LLMResponse(BaseModel):
    parsed: dict
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
async def call_llm_structured(
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
    temperature: float = 0.0,
    timeout: float = 120.0,
) -> tuple[T, LLMResponse]:
    """Call OpenAI with structured output, returning parsed result + metadata."""
    client = get_openai_client()

    response = await client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_model,
        temperature=temperature,
        timeout=timeout,
    )

    parsed = response.choices[0].message.parsed
    meta = LLMResponse(
        parsed=parsed.model_dump() if parsed else {},
        prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
        completion_tokens=response.usage.completion_tokens if response.usage else 0,
        total_tokens=response.usage.total_tokens if response.usage else 0,
        model=response.model,
    )

    logger.info(
        "LLM call completed: model=%s, tokens=%d, cost=~$%.4f",
        model,
        meta.total_tokens,
        estimate_cost(model, meta.prompt_tokens, meta.completion_tokens),
    )

    return parsed, meta


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Rough cost estimation based on model pricing."""
    rates = {
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
        "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
    }
    input_rate, output_rate = rates.get(model, (0.0, 0.0))
    return (prompt_tokens * input_rate) + (completion_tokens * output_rate)
