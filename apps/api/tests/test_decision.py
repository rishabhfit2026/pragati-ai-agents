from dataclasses import dataclass

from app.agents import decision


@dataclass
class FakeMatch:
    status: str


@dataclass
class FakeCompliance:
    status: str
    title: str = "x"


def test_high_score_no_gaps_is_pursue():
    reqs = [{"mandatory": True, "category": "ballistic"}]
    matches = [FakeMatch("MATCH")]
    result = decision.decide(
        final_score=85, requirements=reqs, capability_matches=matches, compliance_results=[],
        score_explanation={"strengths": [], "concerns": []},
    )
    assert result.recommendation == "PURSUE"


def test_low_score_is_do_not_pursue():
    reqs = [{"mandatory": True, "category": "ballistic"}]
    matches = [FakeMatch("MATCH")]
    result = decision.decide(
        final_score=30, requirements=reqs, capability_matches=matches, compliance_results=[],
        score_explanation={"strengths": [], "concerns": []},
    )
    assert result.recommendation == "DO_NOT_PURSUE"


def test_single_mandatory_capability_gap_forces_review_even_with_high_score():
    reqs = [{"mandatory": True, "category": "ballistic"}]
    matches = [FakeMatch("GAP")]
    result = decision.decide(
        final_score=90, requirements=reqs, capability_matches=matches, compliance_results=[],
        score_explanation={"strengths": [], "concerns": []},
    )
    assert result.recommendation == "REVIEW"


def test_two_mandatory_gaps_forces_do_not_pursue_even_with_high_score():
    reqs = [{"mandatory": True, "category": "ballistic"}, {"mandatory": True, "category": "ballistic"}]
    matches = [FakeMatch("GAP"), FakeMatch("GAP")]
    result = decision.decide(
        final_score=90, requirements=reqs, capability_matches=matches, compliance_results=[],
        score_explanation={"strengths": [], "concerns": []},
    )
    assert result.recommendation == "DO_NOT_PURSUE"


def test_optional_requirement_gap_is_not_critical():
    reqs = [{"mandatory": False, "category": "ballistic"}]
    matches = [FakeMatch("GAP")]
    result = decision.decide(
        final_score=90, requirements=reqs, capability_matches=matches, compliance_results=[],
        score_explanation={"strengths": [], "concerns": []},
    )
    assert result.recommendation == "PURSUE"
    assert result.reasons["critical_gap_count"] == 0


def test_optional_compliance_gap_does_not_count_as_critical():
    reqs = [{"mandatory": False, "category": "certification"}]
    matches = [FakeMatch("UNKNOWN")]
    compliance = [(0, FakeCompliance("GAP"))]
    result = decision.decide(
        final_score=90, requirements=reqs, capability_matches=matches, compliance_results=compliance,
        score_explanation={"strengths": [], "concerns": []},
    )
    assert result.recommendation == "PURSUE"
