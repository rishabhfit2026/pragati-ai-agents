"""Pragati Capability Matching Agent — section 10.

For every extracted requirement, determines whether Pragati's public
product/capability knowledge base supports it: MATCH, PARTIAL_MATCH, UNKNOWN,
or GAP.

Two implementations:
  - run_llm(): LLM + RAG — retrieve() picks relevant knowledge-base products
    per requirement (see app/knowledge/retriever.py), then a single batched
    LLM call reasons over the retrieved evidence for the whole requirement
    set at once. This is the active path whenever a real LLM provider is
    configured.
  - match_requirement() / run(): deterministic keyword/token overlap scoring.
    Used when no real LLM is available (offline/mock mode), and as an
    automatic per-requirement fallback if the LLM's response for that
    requirement is missing, malformed, or cites a knowledge-base id that was
    never actually offered to it (never trust an uncited MATCH).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.agents.errors import ToolError
from app.knowledge.loader import load_knowledge_base, searchable_product_text

logger = logging.getLogger(__name__)

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


CAPABILITY_MATCH_PROMPT = """You are Pragati Defence Systems' capability-matching analyst. For each \
numbered requirement below, decide whether Pragati's product/capability knowledge base (also provided) \
supports it.

Respond ONLY with a minified JSON array, one object per requirement in the same order, each with:
- "index": the requirement's index (int)
- "status": one of "MATCH", "PARTIAL_MATCH", "UNKNOWN", "GAP"
- "confidence": float 0-1
- "evidence": one sentence citing SPECIFIC facts from the knowledge-base excerpts (or explaining why none apply)
- "kb_reference_id": the "id" field of the knowledge-base product you are citing, or null if none

RULES (be conservative — this feeds a real bid/no-bid business decision, never invent a capability):
- Only use "MATCH" if a specific knowledge-base entry EXPLICITLY and concretely supports this exact requirement.
- Use "PARTIAL_MATCH" if a related product exists but doesn't explicitly confirm this exact spec.
- Use "GAP" if the requirement is clearly outside anything in the knowledge base (e.g. drones, radar, software, cyber, satellites).
- Use "UNKNOWN" otherwise — do not guess.
- "kb_reference_id" MUST be an "id" that literally appears in the knowledge-base excerpts below, or null. Never invent one.

REQUIREMENTS:
{requirements_json}

KNOWLEDGE BASE EXCERPTS (pre-retrieved as relevant to these requirements):
{kb_json}
"""


def run_llm(requirements: list[dict[str, Any]], llm: Any) -> list[MatchResult]:
    from app.knowledge.retriever import retrieve_relevant_products

    candidate_by_id: dict[str, dict] = {}
    for r in requirements:
        for p in retrieve_relevant_products(r["description"], top_k=3):
            candidate_by_id[p["id"]] = p
    candidates = list(candidate_by_id.values())[:24]  # cap prompt size
    valid_ids = {p["id"] for p in candidates}

    req_payload = [
        {"index": i, "description": r["description"], "category": r["category"]}
        for i, r in enumerate(requirements)
    ]
    kb_payload = [{k: v for k, v in p.items() if not k.startswith("_")} for p in candidates]

    prompt = CAPABILITY_MATCH_PROMPT.format(
        requirements_json=json.dumps(req_payload), kb_json=json.dumps(kb_payload)
    )
    raw = llm.complete_json(prompt)

    by_index: dict[int, dict] = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("index"), int):
                by_index[item["index"]] = item

    results: list[MatchResult] = []
    for i, r in enumerate(requirements):
        item = by_index.get(i)
        status = item.get("status") if item else None
        if not item or status not in ("MATCH", "PARTIAL_MATCH", "UNKNOWN", "GAP"):
            results.append(match_requirement(r["description"], r["category"]))
            continue

        kb_ref = item.get("kb_reference_id")
        if kb_ref not in valid_ids:
            # The model cited (or invented) a reference outside what it was
            # actually given — never let an uncited claim stand as a MATCH.
            if status == "MATCH":
                status = "UNKNOWN"
            kb_ref = None
        product = candidate_by_id.get(kb_ref)
        try:
            confidence = float(item.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        results.append(MatchResult(
            status=status,
            confidence=max(0.0, min(confidence, 1.0)),
            evidence=str(item.get("evidence") or "LLM did not provide evidence.")[:400],
            kb_reference_id=kb_ref,
            kb_reference_name=product["name"] if product else None,
        ))
    return results


def run(
    requirements: list[dict[str, Any]], *, llm: Any = None, simulate_failure: str | None = None
) -> list[MatchResult]:
    if simulate_failure == "TOOL_ERROR":
        raise ToolError("Simulated knowledge base lookup failure in Capability Matching Agent")

    if llm is not None and getattr(llm, "supports_generic_completion", False):
        try:
            return run_llm(requirements, llm)
        except Exception as e:
            logger.warning("LLM+RAG capability matching failed, falling back to deterministic scoring: %s", e)

    return [match_requirement(r["description"], r["category"]) for r in requirements]
