"""Requirement Extraction Agent — section 8.

Turns unstructured tender text into structured tender metadata + a list of
typed requirements, each carrying a source page/section/snippet and a
confidence score. Delegates the actual extraction to the configured LLM
provider (mock by default, real providers opt-in).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.llm.provider import LLMProvider, LLMTimeoutError
from app.services.pdf_extract import DocumentExtract

ALLOWED_CATEGORIES = {
    "technical", "ballistic", "material", "dimensional", "performance", "certification",
    "testing", "manufacturing", "documentation", "delivery", "financial", "eligibility",
}


@dataclass
class RequirementExtractionResult:
    metadata: dict[str, Any]
    requirements: list[dict[str, Any]]


def run(
    document: DocumentExtract,
    llm: LLMProvider,
    *,
    simulate_failure: str | None = None,
) -> RequirementExtractionResult:
    if simulate_failure == "LLM_TIMEOUT":
        raise LLMTimeoutError("Simulated LLM timeout during requirement extraction")

    metadata = llm.extract_tender_metadata(document.pages)
    raw_requirements = llm.extract_requirements(document.pages)

    if simulate_failure == "INVALID_JSON":
        # Simulate a provider returning malformed data that fails schema validation,
        # to be retried by the orchestrator.
        raw_requirements = "not-a-list"  # type: ignore[assignment]

    cleaned: list[dict[str, Any]] = []
    if isinstance(raw_requirements, list):
        for r in raw_requirements:
            if not isinstance(r, dict) or not r.get("description"):
                continue
            category = r.get("category") if r.get("category") in ALLOWED_CATEGORIES else "technical"
            cleaned.append(
                {
                    "description": str(r["description"])[:500],
                    "category": category,
                    "mandatory": bool(r.get("mandatory", True)),
                    "confidence": float(r.get("confidence", 0.5)),
                    "source_page": r.get("source_page"),
                    "source_section": r.get("source_section"),
                    "source_text_snippet": r.get("source_text_snippet", r.get("description"))[:300],
                }
            )
    else:
        raise ValueError("Requirement extraction returned malformed data (expected a list)")

    return RequirementExtractionResult(metadata=metadata, requirements=cleaned)
