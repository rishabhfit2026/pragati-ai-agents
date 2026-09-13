"""LLM provider abstraction (section 26). All document content stays server-side;
the frontend never talks to an LLM directly and no API key ever reaches the client.

Two capabilities are exposed:
  - extract_tender_metadata(pages)  -> structured tender header fields
  - extract_requirements(pages)     -> structured requirement list with source refs

The mock provider is deterministic, offline, and used by default so the whole
system is runnable without any API key. Real providers are opt-in via env vars
AND require `allow_external_llm_calls=True`, enforced here rather than trusted
to the caller.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.config import settings
from app.services.pdf_extract import PageExtract


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def extract_tender_metadata(self, pages: list[PageExtract]) -> dict[str, Any]:
        ...

    @abstractmethod
    def extract_requirements(self, pages: list[PageExtract]) -> list[dict[str, Any]]:
        ...


class LLMError(Exception):
    pass


class InvalidJSONError(LLMError):
    pass


class LLMTimeoutError(LLMError):
    pass


def get_llm_provider(provider_override: str | None = None, model_override: str | None = None) -> LLMProvider:
    provider = provider_override or settings.llm_provider
    # Only pass a model kwarg when one was actually chosen — otherwise each
    # provider class's own default model wins (see app/llm/*_provider.py).
    chosen_model = model_override or settings.llm_model
    model_kwargs = {"model": chosen_model} if chosen_model else {}

    if provider == "anthropic" and settings.allow_external_llm_calls and settings.anthropic_api_key:
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(**model_kwargs)

    if provider == "openai" and settings.allow_external_llm_calls and settings.openai_api_key:
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(**model_kwargs)

    if provider == "groq" and settings.allow_external_llm_calls and settings.groq_api_key:
        from app.llm.groq_provider import GroqProvider

        return GroqProvider(**model_kwargs)

    if provider == "nvidia" and settings.allow_external_llm_calls and settings.nvidia_api_key:
        from app.llm.nvidia_provider import NvidiaProvider

        return NvidiaProvider(**model_kwargs)

    from app.llm.mock_provider import MockLLMProvider

    return MockLLMProvider(model=model_override or "mock-analyst-v1")
