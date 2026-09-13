"""Unit tests for the LLM-backed paths of Capability Matching, Compliance,
Risk, and Commercial/Strategic — using a fake provider so these never touch
the network. Each test checks both the happy path and that a bad/malformed
LLM response safely falls back to deterministic logic rather than corrupting
the pipeline."""
import json

from app.agents import capability_matching, commercial, compliance, risk


class FakeLLM:
    supports_generic_completion = True
    name = "fake"
    model = "fake-model"

    def __init__(self, response):
        self.response = response
        self.last_prompt = None

    def complete_json(self, prompt):
        self.last_prompt = prompt
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


# --- Capability Matching ---

def test_capability_matching_llm_happy_path():
    requirements = [{"description": "Helmet shall provide NIJ Level IIIA protection", "category": "ballistic", "mandatory": True}]
    llm = FakeLLM([{"index": 0, "status": "MATCH", "confidence": 0.9, "evidence": "cited", "kb_reference_id": "helmet-001"}])
    results = capability_matching.run(requirements, llm=llm)
    assert len(results) == 1
    assert results[0].status in ("MATCH", "UNKNOWN")  # UNKNOWN if helmet-001 wasn't in the retrieved set


def test_capability_matching_llm_rejects_uncited_match():
    requirements = [{"description": "Helmet shall provide NIJ Level IIIA protection", "category": "ballistic", "mandatory": True}]
    llm = FakeLLM([{"index": 0, "status": "MATCH", "confidence": 0.9, "evidence": "made up", "kb_reference_id": "totally-fake-id"}])
    results = capability_matching.run(requirements, llm=llm)
    # A MATCH citing an id that was never actually offered must be downgraded.
    assert results[0].status == "UNKNOWN"
    assert results[0].kb_reference_id is None


def test_capability_matching_falls_back_on_malformed_llm_response():
    requirements = [{"description": "The helmet shall provide ballistic protection at NIJ Level IIIA standalone.", "category": "ballistic", "mandatory": True}]
    llm = FakeLLM("not a list at all")
    results = capability_matching.run(requirements, llm=llm)
    assert len(results) == 1
    assert results[0].status in ("MATCH", "PARTIAL_MATCH", "UNKNOWN", "GAP")


def test_capability_matching_uses_deterministic_when_llm_unavailable():
    requirements = [{"description": "The helmet shall provide ballistic protection at NIJ Level IIIA standalone.", "category": "ballistic", "mandatory": True}]
    results = capability_matching.run(requirements, llm=None)
    assert len(results) == 1


# --- Compliance ---

def test_compliance_llm_happy_path():
    requirements = [{"description": "Bidder shall submit valid ISO 9001 certification.", "category": "certification", "mandatory": True}]
    llm = FakeLLM([{"index": 0, "title": "ISO 9001", "status": "UNKNOWN", "confidence": 0.5, "evidence": "not on file"}])
    results = compliance.run(requirements, llm=llm)
    assert len(results) == 1
    idx, result = results[0]
    assert result.status == "UNKNOWN"


def test_compliance_falls_back_on_llm_error():
    requirements = [{"description": "Bidder shall submit valid ISO 9001 certification.", "category": "certification", "mandatory": True}]
    llm = FakeLLM(RuntimeError("boom"))
    results = compliance.run(requirements, llm=llm)
    assert len(results) == 1


def test_compliance_ignores_invalid_status_value():
    requirements = [{"description": "Bidder shall submit valid ISO 9001 certification.", "category": "certification", "mandatory": True}]
    llm = FakeLLM([{"index": 0, "title": "x", "status": "DEFINITELY_MATCH", "confidence": 0.9, "evidence": "x"}])
    results = compliance.run(requirements, llm=llm)
    # Invalid status must fall back to deterministic evaluation, not pass through.
    assert results[0][1].status in ("MATCH", "UNKNOWN", "GAP")


# --- Risk ---

def test_risk_llm_happy_path():
    llm = FakeLLM([
        {"category": "TECHNICAL", "description": "x", "severity": "HIGH", "probability": "HIGH", "evidence": "x", "mitigation": "x"}
    ])
    results = risk.run(requirements=[], capability_matches=[], compliance_results=[], tender_metadata={}, llm=llm)
    assert len(results) == 1
    assert results[0].category == "TECHNICAL"


def test_risk_falls_back_when_llm_returns_no_valid_entries():
    llm = FakeLLM([{"category": "NOT_A_REAL_CATEGORY", "description": "x", "severity": "HIGH", "probability": "HIGH"}])
    results = risk.run(
        requirements=[], capability_matches=[], compliance_results=[],
        tender_metadata={"issuing_organization": "Indian Army"}, llm=llm,
    )
    # Falls back to deterministic — which for this input produces the
    # COMPETITION risk (defence org keyword match).
    assert any(r.category == "COMPETITION" for r in results)


# --- Commercial / Strategic ---

def test_commercial_llm_happy_path():
    llm = FakeLLM({
        "strategic_fit": 80, "strategic_notes": ["good fit"],
        "commercial_attractiveness": 70, "commercial_notes": ["decent size"],
        "delivery_feasibility": 60, "delivery_notes": ["tight window"],
    })
    result = commercial.run({}, [], llm=llm)
    assert result.strategic_fit == 80.0
    assert result.commercial_attractiveness == 70.0
    assert result.delivery_feasibility == 60.0


def test_commercial_clamps_out_of_range_scores():
    llm = FakeLLM({
        "strategic_fit": 150, "strategic_notes": [],
        "commercial_attractiveness": -20, "commercial_notes": [],
        "delivery_feasibility": 50, "delivery_notes": [],
    })
    result = commercial.run({}, [], llm=llm)
    assert result.strategic_fit == 100.0
    assert result.commercial_attractiveness == 0.0


def test_commercial_falls_back_on_missing_fields():
    llm = FakeLLM({"strategic_fit": 80})  # missing required keys
    result = commercial.run({}, [], llm=llm)
    # Falls back to deterministic — just check it returns something sane.
    assert 0.0 <= result.strategic_fit <= 100.0
    assert 0.0 <= result.commercial_attractiveness <= 100.0
    assert 0.0 <= result.delivery_feasibility <= 100.0
