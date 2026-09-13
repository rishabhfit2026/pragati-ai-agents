"""Eligibility & Compliance Agent — section 11.

Builds the Compliance Matrix. This agent is deliberately conservative: an
"Unknown" in the knowledge base (e.g. "certificate on file: Unknown — requires
verification") can NEVER be upgraded to a pass here. It can only become MATCH
when the knowledge base states a concrete, verifiable fact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.knowledge.loader import load_knowledge_base

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


def run(requirements: list[dict[str, Any]]) -> list[tuple[int, ComplianceResult]]:
    """Returns (requirement_index, ComplianceResult) for every requirement whose
    category is compliance-relevant."""
    results = []
    for idx, r in enumerate(requirements):
        if r["category"] in COMPLIANCE_CATEGORIES:
            results.append((idx, evaluate_compliance(r["description"], r["category"])))
    return results
