"""Base class for any provider that speaks the OpenAI chat-completions wire
format — OpenAI itself, Groq, and NVIDIA NIM all qualify. Only the base URL,
API key, and default model differ between them."""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.anthropic_provider import METADATA_PROMPT, REQUIREMENTS_PROMPT
from app.llm.provider import LLMProvider, InvalidJSONError, LLMProviderError, LLMTimeoutError
from app.services.pdf_extract import PageExtract


class OpenAICompatibleProvider(LLMProvider):
    base_url: str
    supports_json_mode: bool = True

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def _call(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"}
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        if self.supports_json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            resp = httpx.post(self.base_url, headers=headers, json=payload, timeout=60)
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(str(e)) from e
        except httpx.HTTPError as e:
            raise LLMProviderError(f"{self.name}: connection error: {e}") from e

        if resp.status_code >= 400:
            # 429 = rate limited, 401/403 = bad/missing key, 5xx = provider outage —
            # all of these mean "this provider can't serve this request right now",
            # which is exactly what a failover chain needs to catch and act on.
            raise LLMProviderError(
                f"{self.name}: HTTP {resp.status_code}: {resp.text[:300]}", status_code=resp.status_code
            )
        return resp.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_json(raw: str) -> Any:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise InvalidJSONError(f"Model did not return valid JSON: {e}") from e

    def extract_tender_metadata(self, pages: list[PageExtract]) -> dict[str, Any]:
        text = "\n\n".join(f"[[PAGE {p.page_number}]]\n{p.text}" for p in pages[:6])
        raw = self._call(METADATA_PROMPT.format(text=text[:12000]))
        result = self._parse_json(raw)
        return result if isinstance(result, dict) else {}

    def extract_requirements(self, pages: list[PageExtract]) -> list[dict[str, Any]]:
        text = "\n\n".join(f"[[PAGE {p.page_number}]]\n{p.text}" for p in pages)
        raw = self._call(REQUIREMENTS_PROMPT.format(text=text[:40000]))
        result = self._parse_json(raw)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            # Some models wrap the array in {"requirements": [...]} even when
            # asked for a bare array — accept that shape too.
            for value in result.values():
                if isinstance(value, list):
                    return value
        return []
