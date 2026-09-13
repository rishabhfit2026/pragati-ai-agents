"""Opportunity Scoring Agent — section 13.

The final score is ALWAYS a deterministic weighted sum of six structured
sub-scores. No LLM ever outputs the score directly — this function is pure
arithmetic over agent outputs, which is what makes the score explainable and
reproducible under replay.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

WEIGHTS = {
    "technical_fit": 0.25,
    "capability_fit": 0.20,
    "compliance_readiness": 0.20,
    "strategic_fit": 0.15,
    "commercial_attractiveness": 0.10,
    "delivery_feasibility": 0.10,
}

# Alternate, stricter weighting profile used by "score-v2" — leans harder on
# compliance/certification readiness. Selectable via replay (section 20) so a
# re-run can demonstrably change the score/recommendation from the same
# extracted facts, without ever touching the underlying agent outputs.
WEIGHTS_V2 = {
    "technical_fit": 0.20,
    "capability_fit": 0.15,
    "compliance_readiness": 0.30,
    "strategic_fit": 0.15,
    "commercial_attractiveness": 0.10,
    "delivery_feasibility": 0.10,
}

WEIGHTS_BY_VERSION = {"score-v1": WEIGHTS, "score-v2": WEIGHTS_V2}

MATCH_WEIGHTS = {"MATCH": 1.0, "PARTIAL_MATCH": 0.6, "UNKNOWN": 0.35, "GAP": 0.0}
COMPLIANCE_WEIGHTS = {"MATCH": 1.0, "UNKNOWN": 0.45, "GAP": 0.0}

DOMAIN_CATEGORIES = {"ballistic", "material", "dimensional", "performance", "technical"}

# Capability Fit deliberately covers engineering + production-capacity
# categories only. Certification/testing/eligibility/documentation/financial/
# delivery are administrative/compliance concerns already scored in full by
# Compliance Readiness — folding them into Capability Fit too would
# double-penalize the same unknowns under two different weights.
CAPABILITY_CATEGORIES = DOMAIN_CATEGORIES | {"manufacturing"}


@dataclass
class ScoreResult:
    technical_fit: float
    capability_fit: float
    compliance_readiness: float
    strategic_fit: float
    commercial_attractiveness: float
    delivery_feasibility: float
    final_score: float
    explanation: dict[str, Any]


def _weighted_average(statuses: list[str], weight_map: dict[str, float]) -> float:
    if not statuses:
        return 60.0  # neutral default when a factor has no applicable data
    total = sum(weight_map.get(s, 0.2) for s in statuses)
    return round((total / len(statuses)) * 100, 1)


def compute_score(
    *,
    requirements: list[dict[str, Any]],
    capability_matches: list[Any],
    compliance_results: list[tuple[int, Any]],
    commercial: Any,
    scoring_version: str = "score-v1",
) -> ScoreResult:
    weights = WEIGHTS_BY_VERSION.get(scoring_version, WEIGHTS)

    domain_statuses = [
        m.status for r, m in zip(requirements, capability_matches) if r["category"] in DOMAIN_CATEGORIES
    ]
    all_statuses = [
        m.status for r, m in zip(requirements, capability_matches) if r["category"] in CAPABILITY_CATEGORIES
    ]
    compliance_statuses = [c.status for _, c in compliance_results]

    technical_fit = _weighted_average(domain_statuses, MATCH_WEIGHTS)
    capability_fit = _weighted_average(all_statuses, MATCH_WEIGHTS)
    compliance_readiness = _weighted_average(compliance_statuses, COMPLIANCE_WEIGHTS)

    sub_scores = {
        "technical_fit": technical_fit,
        "capability_fit": capability_fit,
        "compliance_readiness": compliance_readiness,
        "strategic_fit": commercial.strategic_fit,
        "commercial_attractiveness": commercial.commercial_attractiveness,
        "delivery_feasibility": commercial.delivery_feasibility,
    }
    final_score = round(sum(sub_scores[k] * weights[k] for k in weights), 1)

    strengths, concerns = [], []
    for key, value in sub_scores.items():
        label = key.replace("_", " ").title()
        if value >= 80:
            strengths.append(f"Strong {label} ({value}/100).")
        elif value <= 45:
            concerns.append(f"Weak {label} ({value}/100).")

    gap_count = sum(1 for s in all_statuses if s == "GAP")
    unknown_compliance_count = sum(1 for s in compliance_statuses if s == "UNKNOWN")
    if gap_count:
        concerns.append(f"{gap_count} requirement(s) have no confirmed Pragati capability.")
    if unknown_compliance_count:
        concerns.append(f"{unknown_compliance_count} compliance item(s) are unverified (certifications/eligibility).")

    explanation = {
        "weights": weights,
        "scoring_version": scoring_version,
        "sub_scores": sub_scores,
        "strengths": strengths[:5],
        "concerns": concerns[:5],
        "strategic_notes": commercial.strategic_notes,
        "commercial_notes": commercial.commercial_notes,
        "delivery_notes": commercial.delivery_notes,
    }

    return ScoreResult(
        technical_fit=technical_fit,
        capability_fit=capability_fit,
        compliance_readiness=compliance_readiness,
        strategic_fit=commercial.strategic_fit,
        commercial_attractiveness=commercial.commercial_attractiveness,
        delivery_feasibility=commercial.delivery_feasibility,
        final_score=final_score,
        explanation=explanation,
    )
