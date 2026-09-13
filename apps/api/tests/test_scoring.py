from dataclasses import dataclass

from app.agents import scoring


@dataclass
class FakeMatch:
    status: str


@dataclass
class FakeCompliance:
    status: str
    title: str = "x"


@dataclass
class FakeCommercial:
    strategic_fit: float
    strategic_notes: list
    commercial_attractiveness: float
    commercial_notes: list
    delivery_feasibility: float
    delivery_notes: list


def _commercial(strategic=90.0, commercial=80.0, delivery=85.0):
    return FakeCommercial(strategic, [], commercial, [], delivery, [])


def test_all_matches_yields_perfect_technical_and_capability_fit():
    reqs = [{"category": "ballistic", "mandatory": True}] * 4
    matches = [FakeMatch("MATCH")] * 4
    result = scoring.compute_score(
        requirements=reqs, capability_matches=matches, compliance_results=[], commercial=_commercial()
    )
    assert result.technical_fit == 100.0
    assert result.capability_fit == 100.0


def test_all_gaps_yields_zero_technical_fit():
    reqs = [{"category": "ballistic", "mandatory": True}] * 3
    matches = [FakeMatch("GAP")] * 3
    result = scoring.compute_score(
        requirements=reqs, capability_matches=matches, compliance_results=[], commercial=_commercial()
    )
    assert result.technical_fit == 0.0


def test_final_score_is_deterministic_weighted_sum():
    reqs = [{"category": "ballistic", "mandatory": True}]
    matches = [FakeMatch("MATCH")]
    result = scoring.compute_score(
        requirements=reqs, capability_matches=matches, compliance_results=[], commercial=_commercial(),
        scoring_version="score-v1",
    )
    expected = round(sum(
        {
            "technical_fit": 100.0, "capability_fit": 100.0, "compliance_readiness": 60.0,
            "strategic_fit": 90.0, "commercial_attractiveness": 80.0, "delivery_feasibility": 85.0,
        }[k] * scoring.WEIGHTS[k]
        for k in scoring.WEIGHTS
    ), 1)
    assert result.final_score == expected


def test_scoring_version_changes_weights_and_can_change_final_score():
    reqs = [{"category": "ballistic", "mandatory": True}]
    matches = [FakeMatch("MATCH")]
    compliance = [(0, FakeCompliance("UNKNOWN"))]

    v1 = scoring.compute_score(
        requirements=reqs, capability_matches=matches, compliance_results=compliance,
        commercial=_commercial(), scoring_version="score-v1",
    )
    v2 = scoring.compute_score(
        requirements=reqs, capability_matches=matches, compliance_results=compliance,
        commercial=_commercial(), scoring_version="score-v2",
    )
    # Same underlying facts, different weighting policy -> different final score.
    assert v1.final_score != v2.final_score
    assert v1.explanation["weights"] != v2.explanation["weights"]


def test_capability_fit_excludes_pure_compliance_categories():
    # A 'financial' or 'documentation' requirement's capability-match status
    # must not affect Capability Fit — that is compliance's job.
    reqs = [
        {"category": "ballistic", "mandatory": True},
        {"category": "financial", "mandatory": True},
    ]
    matches = [FakeMatch("MATCH"), FakeMatch("GAP")]
    result = scoring.compute_score(
        requirements=reqs, capability_matches=matches, compliance_results=[], commercial=_commercial()
    )
    assert result.capability_fit == 100.0
