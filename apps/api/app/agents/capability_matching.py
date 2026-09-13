"""Pragati Capability Matching Agent — section 10.

For every extracted requirement, determines whether Pragati's public
product/capability knowledge base supports it: MATCH, PARTIAL_MATCH, UNKNOWN,
or GAP. Matching is done with transparent keyword/token overlap scoring (not
an opaque LLM judgement) so every verdict can show its evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.agents.errors import ToolError
from app.knowledge.loader import load_knowledge_base, searchable_product_text

STOPWORDS = {
    "the", "and", "for", "with", "shall", "must", "should", "this", "that", "from", "will",
    "have", "been", "are", "was", "were", "any", "all", "not", "least", "more", "than", "per",
    "each", "such", "under", "over", "into", "also", "may", "can", "which", "their", "its",
    "provided", "including", "provide", "provides", "required", "requirement", "requirements",
}

TOKEN_RE = re.compile(r"[a-z0-9.]+")

DOMAIN_CATEGORIES = {"ballistic", "material", "dimensional", "performance", "technical"}
GAP_PRONE_KEYWORDS = ["drone", "uav", "radar", "sonar", "satellite", "software", "cyber", "avionics", "missile"]


def tokenize(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(text.lower()) if len(t) > 2 and t not in STOPWORDS}


def overlap_score(req_tokens: set[str], candidate_tokens: set[str]) -> tuple[float, int]:
    """Containment of the requirement's vocabulary within the candidate's
    vocabulary — i.e. 'how much of what this requirement asks for is
    addressed by this product's public spec'. Requirement text is short and
    a knowledge-base entry's text is comparatively large, so a symmetric
    (Jaccard) measure would under-score even a strong match; containment is
    the right shape for "does the candidate cover the requirement." Returns
    (score, raw_intersection_count) — the count guards against a spurious
    match on a single common word."""
    if not req_tokens or not candidate_tokens:
        return 0.0, 0
    intersection = req_tokens & candidate_tokens
    return len(intersection) / len(req_tokens), len(intersection)


@dataclass
class MatchResult:
    status: str
    confidence: float
    evidence: str
    kb_reference_id: str | None
    kb_reference_name: str | None


def match_requirement(description: str, category: str) -> MatchResult:
    # A requirement that explicitly names a domain Pragati's public knowledge
    # base has nothing in (drones, radar, cyber, etc.) is a GAP even if a
    # generic word ("system", "integrated") happens to overlap with some
    # unrelated product's spec text — that superficial overlap is not real
    # evidence of capability, and conservatism wins the tie.
    if any(kw in description.lower() for kw in GAP_PRONE_KEYWORDS):
        return MatchResult(
            status="GAP",
            confidence=0.8,
            evidence="No Pragati product/capability in the public knowledge base addresses this domain.",
            kb_reference_id=None,
            kb_reference_name=None,
        )

    kb = load_knowledge_base()
    req_tokens = tokenize(description)

    best_product = None
    best_score = 0.0
    best_hits = 0
    for product in kb["products"]:
        score, hits = overlap_score(req_tokens, tokenize(searchable_product_text(product)))
        if score > best_score:
            best_score, best_hits, best_product = score, hits, product

    if best_product and best_score >= 0.32 and best_hits >= 2:
        return MatchResult(
            status="MATCH",
            confidence=round(min(0.65 + best_score * 0.3, 0.96), 2),
            evidence=f"Public spec for '{best_product['name']}' ({best_product.get('category')}) overlaps strongly with this requirement.",
            kb_reference_id=best_product["id"],
            kb_reference_name=best_product["name"],
        )

    if best_product and best_score >= 0.18 and best_hits >= 1:
        return MatchResult(
            status="PARTIAL_MATCH",
            confidence=round(0.45 + best_score * 0.3, 2),
            evidence=(
                f"'{best_product['name']}' is in a related product line, but the public spec does not "
                "explicitly confirm this exact requirement — needs engineering confirmation."
            ),
            kb_reference_id=best_product["id"],
            kb_reference_name=best_product["name"],
        )

    if category in DOMAIN_CATEGORIES:
        return MatchResult(
            status="UNKNOWN",
            confidence=0.4,
            evidence="Requirement is in a domain Pragati operates in, but no specific public evidence confirms this exact spec.",
            kb_reference_id=None,
            kb_reference_name=None,
        )

    return MatchResult(
        status="UNKNOWN",
        confidence=0.35,
        evidence="No direct evidence found in the public/synthetic knowledge base for this requirement.",
        kb_reference_id=None,
        kb_reference_name=None,
    )


def run(requirements: list[dict[str, Any]], *, simulate_failure: str | None = None) -> list[MatchResult]:
    if simulate_failure == "TOOL_ERROR":
        raise ToolError("Simulated knowledge base lookup failure in Capability Matching Agent")
    return [match_requirement(r["description"], r["category"]) for r in requirements]
