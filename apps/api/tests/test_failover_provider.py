import pytest

from app.llm.failover_provider import AllProvidersFailedError, FailoverLLMProvider
from app.llm.provider import LLMProviderError


class FakeProvider:
    supports_generic_completion = False

    def __init__(self, name, model, fail=False, requirements=None):
        self.name = name
        self.model = model
        self.fail = fail
        self._requirements = requirements or []

    def extract_tender_metadata(self, pages):
        if self.fail:
            raise LLMProviderError(f"{self.name}: HTTP 429 rate limited", status_code=429)
        return {"title": f"handled by {self.name}"}

    def extract_requirements(self, pages):
        if self.fail:
            raise LLMProviderError(f"{self.name}: HTTP 429 rate limited", status_code=429)
        return self._requirements


def test_falls_over_to_second_provider_on_rate_limit():
    p1 = FakeProvider("groq", "llama-3.3-70b", fail=True)
    p2 = FakeProvider("gemini", "gemini-2.0-flash", fail=False)
    chain = FailoverLLMProvider([p1, p2])

    result = chain.extract_tender_metadata([])
    assert result == {"title": "handled by gemini"}
    assert chain.last_used is p2
    assert chain.last_used_label == "gemini:gemini-2.0-flash"


def test_first_provider_succeeds_without_touching_second():
    p1 = FakeProvider("groq", "llama-3.3-70b", fail=False)
    p2 = FakeProvider("gemini", "gemini-2.0-flash", fail=True)
    chain = FailoverLLMProvider([p1, p2])

    result = chain.extract_tender_metadata([])
    assert result == {"title": "handled by groq"}
    assert chain.last_used is p1


def test_all_providers_failing_raises_a_clear_error():
    p1 = FakeProvider("groq", "llama-3.3-70b", fail=True)
    p2 = FakeProvider("gemini", "gemini-2.0-flash", fail=True)
    chain = FailoverLLMProvider([p1, p2])

    with pytest.raises(AllProvidersFailedError):
        chain.extract_tender_metadata([])


def test_third_provider_in_chain_is_reached_when_first_two_fail():
    p1 = FakeProvider("groq", "llama-3.3-70b", fail=True)
    p2 = FakeProvider("gemini", "gemini-2.0-flash", fail=True)
    p3 = FakeProvider("nvidia", "nvidia/llama-3.1-nemotron-70b-instruct", fail=False, requirements=[{"description": "x"}])
    chain = FailoverLLMProvider([p1, p2, p3])

    result = chain.extract_requirements([])
    assert result == [{"description": "x"}]
    assert chain.last_used is p3
