"""Eligibility & Compliance Agent — section 11.

Builds the Compliance Matrix. This agent is deliberately conservative: an
"Unknown" in the knowledge base (e.g. "certificate on file: Unknown — requires
verification") can NEVER be upgraded to a pass here. It can only become MATCH
when the knowledge base states a concrete, verifiable fact.

run_llm() is the active path when a real LLM provider is configured — it
hands the model the full (small) capabilities knowledge base plus every
compliance-relevant requirement in one batched call, with an explicit
instruction that an unverified claim must resolve to UNKNOWN, never MATCH.
evaluate_compliance()/run() is the deterministic rule-based fallback used
offline and whenever the LLM's response can't be trusted at face value.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.knowledge.loader import load_knowledge_base

logger = logging.getLogger(__name__)

COMPLIANCE_CATEGORIES = {"certification", "testing", "eligibility", "documentation", "financial", "manufacturing", "delivery"}

STANDARD_TOKENS = ["nij", "stanag", "bis", "vpam", "aep-55", "aep55", "iso", "mil-std", "milstd", "as9100", "dgqa"]


@dataclass
class ComplianceResult:
    title: str
    status: str
    confidence: float
    evidence: str


def _find_standard(text: str) -> str | None:
    lower = text.lower()
    for token in STANDARD_TOKENS:
        if token in lower:
            return token
    return None


def evaluate_compliance(description: str, category: str) -> ComplianceResult:
    kb = load_knowledge_base()
    certs = kb["capabilities"].get("certifications", {})
    testing = kb["capabilities"].get("testing", {})
    manufacturing = kb["capabilities"].get("manufacturing", {})
    company = kb["company"]
    lower = description.lower()

    if category == "certification":
        standard = _find_standard(description)
        if standard:
            referenced = [
                s for s in certs.get("standards_referenced", [])
                if standard.replace("-", "") in s["standard"].lower().replace("-", "").replace(" ", "")
            ]
            if referenced:
                return ComplianceResult(
                    title=f"Certification: {referenced[0]['standard']}",
                    status="UNKNOWN",
                    confidence=0.55,
                    evidence=(
                        f"Pragati's public product literature references meeting {referenced[0]['standard']}, "
                        "but no certificate number, issuing body, or expiry date is publicly confirmed. "
                        "Compliance team must verify before this can be marked as met."
                    ),
                )
            return ComplianceResult(
                title=f"Certification: {standard.upper()}",
                status="GAP",
                confidence=0.7,
                evidence=f"No public reference to '{standard.upper()}' found anywhere in Pragati's public capability data.",
            )
        return ComplianceResult(
            title="Certification requirement",
            status="UNKNOWN",
            confidence=0.4,
            evidence="Certification standard could not be identified from the requirement text; manual review required.",
        )

    if category == "testing":
        if any(k in lower for k in ["accredited", "nabl", "third-party", "third party", "independent lab"]):
            return ComplianceResult(
                title="Independent/accredited test verification",
                status="UNKNOWN",
                confidence=0.5,
                evidence=(
                    "Pragati states it uses third-party test reports, but no accredited lab name/certificate is "
                    f"publicly published ({testing.get('accredited_lab_partnerships', 'Unknown — requires verification')})."
                ),
            )
        return ComplianceResult(
            title="Ballistic test capability",
            status="MATCH",
            confidence=0.6,
            evidence="Pragati publicly states it operates an in-house independent ballistic testing laboratory with documented failure logs.",
        )

    if category == "eligibility":
        if any(k in lower for k in ["oem", "own manufacturing", "own facility", "in-house"]):
            return ComplianceResult(
                title="OEM / own-manufacturing eligibility",
                status="MATCH",
                confidence=0.75,
                evidence=f"Pragati operates its own manufacturing facility ('{company.get('manufacturing_facility', 'Pragati Works')}').",
            )
        if any(k in lower for k in ["turnover", "annual revenue", "financial capacity", "net worth"]):
            return ComplianceResult(
                title="Financial/turnover eligibility",
                status="UNKNOWN",
                confidence=0.4,
                evidence="Annual revenue / turnover is not publicly published — must be confirmed by finance team.",
            )
        if any(k in lower for k in ["experience of", "years of experience", "years in business"]):
            return ComplianceResult(
                title="Experience eligibility",
                status="UNKNOWN",
                confidence=0.5,
                evidence=f"Company was founded in {company.get('founded', 'an unpublished year')}; whether this meets the stated minimum experience window requires verification.",
            )
        return ComplianceResult(
            title="Eligibility condition",
            status="UNKNOWN",
            confidence=0.4,
            evidence="Eligibility condition requires manual BD/legal review against company registration documents.",
        )

    if category == "manufacturing":
        if any(k in lower for k in ["capacity", "scale", "volume", "units per"]):
            return ComplianceResult(
                title="Manufacturing capacity",
                status="UNKNOWN",
                confidence=0.4,
                evidence=f"Only spall-liner throughput is publicly disclosed ({manufacturing.get('stated_capacity', {}).get('spall_liner', 'unknown')}); full-line capacity for this product is not published.",
            )
        return ComplianceResult(
            title="Manufacturing facility",
            status="MATCH",
            confidence=0.7,
            evidence="Pragati operates an in-house facility (Pragati Works) covering aramid, UHMWPE, and ceramic composite processing.",
        )

    if category == "financial":
        return ComplianceResult(
            title="Financial requirement (EMD/PBG/payment terms)",
            status="UNKNOWN",
            confidence=0.35,
            evidence="Financial capacity and bid/performance guarantee arrangements are internal and not covered by public data.",
        )

    if category == "delivery":
        return ComplianceResult(
            title="Delivery condition",
            status="UNKNOWN",
            confidence=0.4,
            evidence="Delivery timeline feasibility depends on current production backlog, which is not publicly available.",
        )

    # documentation
    if any(k in lower for k in ["datasheet", "technical literature", "brochure"]):
        return ComplianceResult(
            title="Technical documentation",
            status="MATCH",
            confidence=0.6,
            evidence="Pragati publishes technical datasheets for its product range.",
        )
    return ComplianceResult(
        title="Documentation requirement",
        status="UNKNOWN",
        confidence=0.35,
        evidence="Specific document (undertaking, affidavit, certificate copy) availability must be confirmed internally.",
    )


COMPLIANCE_PROMPT = """You are Pragati Defence Systems' compliance analyst. For each numbered requirement \
below, decide the compliance status using ONLY the knowledge-base facts provided.

Respond ONLY with a minified JSON array, one object per requirement in the same order, each with:
- "index": the requirement's index (int)
- "title": a short (<=6 word) label for this compliance item
- "status": one of "MATCH", "UNKNOWN", "GAP"
- "confidence": float 0-1
- "evidence": one sentence, citing the specific knowledge-base fact you used (or explaining why none applies)

RULES — you are conservative because this feeds a real bid/no-bid decision:
- A knowledge-base field explicitly marked "Unknown — requires verification" can NEVER become "MATCH".
  If the requirement asks about something the knowledge base marks unverified, the status MUST be "UNKNOWN".
- Only use "MATCH" when the knowledge base states a concrete, verifiable, unambiguous fact that satisfies
  the requirement (e.g. "Pragati operates its own manufacturing facility" satisfies an OEM/own-facility ask).
- Use "GAP" only when the knowledge base gives no relevant information AND public reasoning strongly suggests
  it is not met (e.g. a specific certification standard never mentioned anywhere in the knowledge base).
- Use "UNKNOWN" for everything else — this is the default, not a last resort.
- Never invent a fact that is not literally present in the knowledge base below.

REQUIREMENTS:
{requirements_json}

KNOWLEDGE BASE (capabilities + company facts):
{kb_json}
"""


def run_llm(requirements: list[dict[str, Any]], llm: Any) -> list[tuple[int, ComplianceResult]]:
    compliance_items = [(i, r) for i, r in enumerate(requirements) if r["category"] in COMPLIANCE_CATEGORIES]
    if not compliance_items:
        return []

    kb = load_knowledge_base()
    kb_payload = {"capabilities": kb["capabilities"], "company": kb["company"]}
    req_payload = [
        {"index": i, "description": r["description"], "category": r["category"], "mandatory": r["mandatory"]}
        for i, r in compliance_items
    ]

    prompt = COMPLIANCE_PROMPT.format(requirements_json=json.dumps(req_payload), kb_json=json.dumps(kb_payload))
    raw = llm.complete_json(prompt)

    by_index: dict[int, dict] = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("index"), int):
                by_index[item["index"]] = item

    results: list[tuple[int, ComplianceResult]] = []
    for i, r in compliance_items:
        item = by_index.get(i)
        status = item.get("status") if item else None
        if not item or status not in ("MATCH", "UNKNOWN", "GAP"):
            results.append((i, evaluate_compliance(r["description"], r["category"])))
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        results.append((i, ComplianceResult(
            title=str(item.get("title") or r["category"].title())[:60],
            status=status,
            confidence=max(0.0, min(confidence, 1.0)),
            evidence=str(item.get("evidence") or "LLM did not provide evidence.")[:400],
        )))
    return results


def run(requirements: list[dict[str, Any]], *, llm: Any = None) -> list[tuple[int, ComplianceResult]]:
    """Returns (requirement_index, ComplianceResult) for every requirement whose
    category is compliance-relevant."""
    if llm is not None and getattr(llm, "supports_generic_completion", False):
        try:
            return run_llm(requirements, llm)
        except Exception as e:
            logger.warning("LLM-based compliance evaluation failed, falling back to deterministic rules: %s", e)

    results = []
    for idx, r in enumerate(requirements):
        if r["category"] in COMPLIANCE_CATEGORIES:
            results.append((idx, evaluate_compliance(r["description"], r["category"])))
    return results
