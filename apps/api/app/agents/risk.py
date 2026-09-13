"""Risk Analysis Agent — section 12.

Derives risk register entries deterministically from the outputs of the
capability-matching and compliance agents, plus a few tender-metadata
heuristics (quantity vs. published capacity, tight delivery windows).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.agents.commercial import DEFENCE_ORG_KEYWORDS
from app.knowledge.loader import load_knowledge_base

QUANTITY_RE = re.compile(r"([\d,]{3,})")
TIGHT_DELIVERY_RE = re.compile(r"\b(\d{1,2})\s*(day|days|week|weeks)\b", re.I)


@dataclass
class RiskItem:
    category: str
    description: str
    severity: str
    probability: str
    evidence: str
    mitigation: str


def run(
    *,
    requirements: list[dict[str, Any]],
    capability_matches: list[Any],
    compliance_results: list[tuple[int, Any]],
    tender_metadata: dict[str, Any],
) -> list[RiskItem]:
    risks: list[RiskItem] = []
    kb = load_knowledge_base()

    # --- TECHNICAL / mandatory capability gaps ---
    gap_reqs = [
        (r, m) for r, m in zip(requirements, capability_matches)
        if m.status == "GAP" and r["mandatory"]
    ]
    for r, m in gap_reqs:
        risks.append(RiskItem(
            category="TECHNICAL",
            description=f"No confirmed Pragati capability for mandatory requirement: \"{r['description'][:120]}\"",
            severity="HIGH",
            probability="HIGH",
            evidence=m.evidence,
            mitigation="Engineering review to confirm whether this can be developed, subcontracted, or partnered for this bid.",
        ))

    # --- COMPLIANCE / certification & eligibility gaps and unknowns ---
    compliance_gap_count = 0
    compliance_unknown_count = 0
    for idx, c in compliance_results:
        if c.status == "GAP":
            compliance_gap_count += 1
            risks.append(RiskItem(
                category="COMPLIANCE",
                description=f"{c.title} — no public evidence of compliance.",
                severity="HIGH",
                probability="MEDIUM",
                evidence=c.evidence,
                mitigation="Compliance/legal team to confirm current certification status before bid submission.",
            ))
        elif c.status == "UNKNOWN":
            compliance_unknown_count += 1
    if compliance_unknown_count >= 2:
        risks.append(RiskItem(
            category="COMPLIANCE",
            description=f"{compliance_unknown_count} compliance items (certifications/eligibility/financial) are unverified.",
            severity="MEDIUM",
            probability="HIGH",
            evidence="Multiple compliance requirements resolved to UNKNOWN — see Compliance Matrix.",
            mitigation="Assign compliance owner to verify all UNKNOWN items before the internal go/no-go review.",
        ))

    # --- DELIVERY ---
    delivery_text = " ".join(r["description"] for r in requirements if r["category"] == "delivery")
    delivery_text += " " + str(tender_metadata.get("delivery_deadline") or "")
    tight_match = TIGHT_DELIVERY_RE.search(delivery_text)
    if tight_match and (tight_match.group(2).lower().startswith("day") or int(tight_match.group(1)) <= 4):
        risks.append(RiskItem(
            category="DELIVERY",
            description=f"Delivery window appears tight ({tight_match.group(0)}).",
            severity="MEDIUM",
            probability="MEDIUM",
            evidence=f"Detected delivery phrase: '{tight_match.group(0)}' in tender text.",
            mitigation="Confirm current production backlog and lead time with Pragati Works before committing.",
        ))

    # --- OPERATIONAL / capacity vs quantity ---
    qty_text = str(tender_metadata.get("estimated_quantity") or "")
    qty_match = QUANTITY_RE.search(qty_text.replace(",", ""))
    if qty_match and int(qty_match.group(1)) >= 1000:
        risks.append(RiskItem(
            category="OPERATIONAL",
            description=f"Estimated quantity ({qty_match.group(1)} units) is large relative to Pragati's publicly disclosed capacity.",
            severity="MEDIUM",
            probability="MEDIUM",
            evidence=f"Only spall-liner throughput is publicly disclosed ({kb['capabilities'].get('manufacturing', {}).get('stated_capacity', {}).get('spall_liner', 'unknown')}); full-line unit capacity is unpublished.",
            mitigation="Confirm production scale-up plan and subcontracting options with operations before bidding.",
        ))

    # --- DOCUMENTATION ---
    doc_reqs = [r for r in requirements if r["category"] == "documentation" and r["mandatory"]]
    if len(doc_reqs) >= 3:
        risks.append(RiskItem(
            category="DOCUMENTATION",
            description=f"{len(doc_reqs)} mandatory documentation items must be assembled for submission.",
            severity="LOW",
            probability="MEDIUM",
            evidence="See Requirements tab, category=documentation.",
            mitigation="Assign a bid coordinator to track document checklist against submission deadline.",
        ))

    # --- COMMERCIAL ---
    financial_unknowns = [c for _, c in compliance_results if c.title.startswith("Financial")]
    if financial_unknowns:
        risks.append(RiskItem(
            category="COMMERCIAL",
            description="Bid security / financial terms require internal finance sign-off.",
            severity="LOW",
            probability="MEDIUM",
            evidence="Financial requirements (EMD/PBG/payment terms) are not addressed by public capability data.",
            mitigation="Route to finance for EMD/PBG arrangement before submission.",
        ))

    # --- COMPETITION (heuristic, always included at low/medium confidence) ---
    org = str(tender_metadata.get("issuing_organization") or "").lower()
    if any(k in org for k in DEFENCE_ORG_KEYWORDS):
        risks.append(RiskItem(
            category="COMPETITION",
            description="High-profile government/defence tenders typically attract multiple established bidders.",
            severity="MEDIUM",
            probability="MEDIUM",
            evidence=f"Issuing organization '{tender_metadata.get('issuing_organization')}' is a defence/government body.",
            mitigation="Competitive/pricing analysis recommended before final bid submission.",
        ))

    return risks
