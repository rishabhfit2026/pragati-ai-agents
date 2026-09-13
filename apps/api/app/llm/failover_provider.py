"""Chains multiple real LLM providers and falls over to the next one on any
failure (rate limit, auth error, provider outage, timeout, or a response that
fails to parse as valid JSON). Built for exactly the situation of stacking
several free-tier keys (Groq, Gemini, NVIDIA/Nemotron, ...) so a rate limit on
one doesn't stall the pipeline.

Each of the two calls the Requirement Extraction Agent makes
(extract_tender_metadata, extract_requirements) tries providers independently
and in order — if Groq serves the metadata call but is then rate-limited for
the (larger) requirements call, that second call simply moves on to Gemini.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from app.llm.provider import LLMError, LLMProvider
from app.services.pdf_extract import PageExtract

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AllProvidersFailedError(LLMError):
    pass


class FailoverLLMProvider(LLMProvider):
    name = "failover"

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("FailoverLLMProvider needs at least one underlying provider")
        self.providers = providers
        self.last_used: LLMProvider | None = None
        self.model = "+".join(f"{p.name}:{p.model}" for p in providers)
        self.supports_generic_completion = any(p.supports_generic_completion for p in providers)

    def _try_each(self, fn: Callable[[LLMProvider], T]) -> T:
        errors: list[str] = []
        for provider in self.providers:
            try:
                result = fn(provider)
            except LLMError as e:
                logger.warning("LLM provider %s failed, trying next: %s", provider.name, e)
                errors.append(f"{provider.name}: {e}")
                continue
            except Exception as e:  # noqa: BLE001 - any provider-side failure should trigger failover
                logger.warning("LLM provider %s raised unexpectedly, trying next: %s", provider.name, e)
                errors.append(f"{provider.name}: {e}")
                continue
            self.last_used = provider
            return result
        raise AllProvidersFailedError(
            f"All {len(self.providers)} LLM provider(s) failed: " + " | ".join(errors)
        )

    @property
    def last_used_label(self) -> str | None:
        return f"{self.last_used.name}:{self.last_used.model}" if self.last_used else None

    def extract_tender_metadata(self, pages: list[PageExtract]) -> dict[str, Any]:
        return self._try_each(lambda p: p.extract_tender_metadata(pages))

    def extract_requirements(self, pages: list[PageExtract]) -> list[dict[str, Any]]:
        return self._try_each(lambda p: p.extract_requirements(pages))

    def complete_json(self, prompt: str) -> Any:
        capable = [p for p in self.providers if p.supports_generic_completion]
        if not capable:
            raise NotImplementedError("No provider in this failover chain supports generic completions")
        errors: list[str] = []
        for provider in capable:
            try:
                result = provider.complete_json(prompt)
            except LLMError as e:
                logger.warning("LLM provider %s failed, trying next: %s", provider.name, e)
                errors.append(f"{provider.name}: {e}")
                continue
            except Exception as e:  # noqa: BLE001
                logger.warning("LLM provider %s raised unexpectedly, trying next: %s", provider.name, e)
                errors.append(f"{provider.name}: {e}")
                continue
            self.last_used = provider
            return result
        raise AllProvidersFailedError(f"All {len(capable)} LLM provider(s) failed: " + " | ".join(errors))
