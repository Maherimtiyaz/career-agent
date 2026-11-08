"""Provider-agnostic LLM client with graceful fallback.

All providers speak the OpenAI chat-completions format, so one AsyncOpenAI
client covers Gemini, Groq, OpenRouter, and any future addition. The chain
is tried in order; a 429, 5xx, timeout, or network error moves to the next
provider. If all fail, LLMProviderError is raised — callers (the orchestrator)
should surface this as a user-visible pause rather than retry infinitely.

BYOK: callers can pass `user_gemini_key` (already decrypted by the API layer)
to override the system-level GEMINI_API_KEY for a single call. This is how
per-user keys are supported without ever logging or persisting them.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

from app.core.config import get_settings


logger = logging.getLogger(__name__)


GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
GROQ_OPENAI_BASE = "https://api.groq.com/openai/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
OPENROUTER_DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


class LLMProviderError(RuntimeError):
    """All providers in the chain failed."""


class LLMResponse(BaseModel):
    """Normalized response shape regardless of underlying provider."""
    content: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    model: str
    provider: str
    usage: dict[str, int] = Field(default_factory=dict)


class ProviderConfig(BaseModel):
    name: str
    base_url: str
    api_key: str
    model: str


def _provider_chain(
    primary_model: str | None = None,
    user_gemini_key: str | None = None,
) -> list[ProviderConfig]:
    """Resolve the ordered provider chain from current settings.

    Order: Gemini primary -> Gemini fallback model -> Groq -> OpenRouter.
    Providers with missing keys are skipped silently — the caller gets a
    clear error if the entire chain is empty.
    """
    settings = get_settings()
    chain: list[ProviderConfig] = []

    gemini_key = user_gemini_key or settings.gemini_api_key
    if gemini_key:
        chosen_primary = primary_model or settings.llm_primary_model
        chain.append(
            ProviderConfig(
                name="gemini-primary",
                base_url=GEMINI_OPENAI_BASE,
                api_key=gemini_key,
                model=chosen_primary,
            )
        )
        if settings.llm_fallback_model and settings.llm_fallback_model != chosen_primary:
            chain.append(
                ProviderConfig(
                    name="gemini-fallback",
                    base_url=GEMINI_OPENAI_BASE,
                    api_key=gemini_key,
                    model=settings.llm_fallback_model,
                )
            )

    if settings.groq_api_key:
        chain.append(
            ProviderConfig(
                name="groq",
                base_url=GROQ_OPENAI_BASE,
                api_key=settings.groq_api_key,
                model=GROQ_DEFAULT_MODEL,
            )
        )

    if settings.openrouter_api_key:
        chain.append(
            ProviderConfig(
                name="openrouter",
                base_url=OPENROUTER_BASE,
                api_key=settings.openrouter_api_key,
                model=OPENROUTER_DEFAULT_MODEL,
            )
        )

    return chain


async def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
    user_gemini_key: str | None = None,
    temperature: float = 0.2,
    timeout: float = 60.0,
    max_tokens: int | None = None,
) -> LLMResponse:
    """Call the first provider in the chain that succeeds."""
    chain = _provider_chain(primary_model=model, user_gemini_key=user_gemini_key)
    if not chain:
        raise LLMProviderError(
            "No LLM providers configured. Set GEMINI_API_KEY (or GROQ_API_KEY / "
            "OPENROUTER_API_KEY) in backend/.env"
        )

    errors: list[str] = []

    for provider in chain:
        try:
            client = AsyncOpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=timeout,
            )
            kwargs: dict[str, Any] = {
                "model": provider.model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            response = await client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            return LLMResponse(
                content=choice.message.content,
                tool_calls=[
                    tc.model_dump() for tc in (choice.message.tool_calls or [])
                ],
                model=provider.model,
                provider=provider.name,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            )
        except (OpenAIError, httpx.HTTPError, Exception) as exc:
            logger.warning(
                "llm_provider_failed",
                extra={"provider": provider.name, "model": provider.model, "error": str(exc)},
            )
            errors.append(f"{provider.name} ({provider.model}): {exc}")
            continue

    raise LLMProviderError(
        "All LLM providers failed. Tried: " + "; ".join(errors)
    )


async def health_check() -> dict[str, Any]:
    """Probe each configured provider with a tiny call. Used by /health/llm."""
    results: dict[str, Any] = {}
    for provider in _provider_chain():
        try:
            client = AsyncOpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=45.0,
            )
            response = await client.chat.completions.create(
                model=provider.model,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
                max_tokens=10,
                temperature=0.0,
            )
            results[provider.name] = {
                "ok": True,
                "model": provider.model,
                "reply": response.choices[0].message.content,
            }
        except Exception as exc:
            results[provider.name] = {
                "ok": False,
                "model": provider.model,
                "error": str(exc),
            }
    return results
