"""Real LLM provider using the Anthropic Messages API. Only ever instantiated
server-side, only when explicitly enabled via ALLOW_EXTERNAL_LLM_CALLS=true and
an ANTHROPIC_API_KEY is present (app/llm/provider.py enforces this gate)."""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings
from app.llm.provider import LLMProvider, InvalidJSONError, LLMTimeoutError
from app.services.pdf_extract import PageExtract

API_URL = "https://api.anthropic.com/v1/messages"

METADATA_PROMPT = """You are a tender/RFP analyst for a defence manufacturer. Extract the tender's \
header metadata from the text below. Respond ONLY with minified JSON with these keys \
(use null if genuinely not present): title, issuing_organization, tender_number, issue_date, \
submission_deadline, delivery_deadline, geography, estimated_quantity, product_category.

TENDER TEXT:
{text}
"""

REQUIREMENTS_PROMPT = """You are a tender/RFP analyst for a defence manufacturer. Extract every \
discrete requirement from the tender text below. Respond ONLY with a minified JSON array; each \
element must have: description, category (one of technical, ballistic, material, dimensional, \
performance, certification, testing, manufacturing, documentation, delivery, financial, eligibility), \
mandatory (bool), confidence (0-1 float), source_page (int), source_section (string or null), \
source_text_snippet (string, verbatim from the text).

TENDER TEXT (pages are marked [[PAGE n]]):
{text}
"""


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-5"):
        self.model = model

    def _call(self, prompt: str) -> str:
        headers = {
            "x-api-key": settings.anthropic_api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            resp = httpx.post(API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(str(e)) from e
        data = resp.json()
        return data["content"][0]["text"]

    @staticmethod
    def _parse_json(raw: str):
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
        return self._parse_json(raw)

    def extract_requirements(self, pages: list[PageExtract]) -> list[dict[str, Any]]:
        text = "\n\n".join(f"[[PAGE {p.page_number}]]\n{p.text}" for p in pages)
        raw = self._call(REQUIREMENTS_PROMPT.format(text=text[:40000]))
        return self._parse_json(raw)
