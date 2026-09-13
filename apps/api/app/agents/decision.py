"""Decision Agent — section 14.

Classification (PURSUE / REVIEW / DO_NOT_PURSUE) is produced by deterministic
business rules over the structured outputs of the earlier agents. The LLM
narrative (used elsewhere for human-readable summaries) never controls this
classification — it only explains it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DecisionResult:
    recommendation: str
    reasons: dict[str, Any]


def decide(
    *,
    final_score: float,
    requirements: list[dict[str, Any]],
    capability_matches: list[Any],
    compliance_results: list[tuple[int, Any]],
    score_explanation: dict[str, Any],
) -> DecisionResult:
    mandatory_gap_capabilities = [
        r for r, m in zip(requirements, capability_matches) if m.status == "GAP" and r["mandatory"]
    ]
    # Only a MANDATORY requirement's compliance gap/unknown is "critical" — an
    # optional ("should"/"preferred") certification that's unmet shouldn't by
    # itself sink the recommendation.
    gap_compliance = [c for idx, c in compliance_results if c.status == "GAP" and requirements[idx]["mandatory"]]
    unknown_compliance = [c for idx, c in compliance_results if c.status == "UNKNOWN" and requirements[idx]["mandatory"]]

    critical_gap_count = len(mandatory_gap_capabilities) + len(gap_compliance)

    if final_score < 50 or critical_gap_count >= 2:
        recommendation = "DO_NOT_PURSUE"
        rule = "score < 50 or 2+ confirmed mandatory gaps"
    elif final_score < 70 or critical_gap_count == 1 or len(unknown_compliance) >= 3:
        recommendation = "REVIEW"
        rule = "score < 70, or a confirmed mandatory gap, or 3+ unverified compliance items"
    elif final_score >= 80 and critical_gap_count == 0:
        recommendation = "PURSUE"
        rule = "score >= 80 with no confirmed mandatory gaps"
    else:
        recommendation = "REVIEW"
        rule = "score in 70-79 band without a disqualifying gap — default to human review"

    why = score_explanation.get("strengths", [])[:3] or ["Overall structured score supports pursuing this opportunity."]
    concerns = score_explanation.get("concerns", [])[:3] or ["No major concerns identified from structured analysis."]

    actions = []
    if unknown_compliance:
        actions.append(f"Verify {len(unknown_compliance)} unresolved compliance/certification item(s) with the compliance team.")
    if mandatory_gap_capabilities:
        actions.append(f"Engineering review of {len(mandatory_gap_capabilities)} mandatory requirement(s) with no confirmed capability match.")
    if gap_compliance:
        actions.append("Legal/compliance sign-off required on unmet certification(s) before proceeding.")
    actions.append("Confirm production capacity and delivery schedule with Pragati Works operations team.")
    if recommendation == "PURSUE":
        actions.insert(0, "Assign bid manager and begin proposal drafting.")

    reasons = {
        "rule_applied": rule,
        "why": why,
        "concerns": concerns,
        "immediate_actions": actions[:5],
        "critical_gap_count": critical_gap_count,
        "unknown_compliance_count": len(unknown_compliance),
    }
    return DecisionResult(recommendation=recommendation, reasons=reasons)
