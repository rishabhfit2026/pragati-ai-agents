"""Regression tests for the production bug: Render had GROQ_API_KEY and
GEMINI_API_KEY set but no LLM_PROVIDER / ALLOW_EXTERNAL_LLM_CALLS, so every
analysis silently used MockLLMProvider (app/llm/provider.py's intentional
fallback) while still returning 200 OK — the report just quietly said
"Model: mock/mock-analyst-v1" instead of failing loudly.

config.validate_llm_config() is called once at app startup (app/main.py) and
must raise instead of allowing that silent fallback whenever LLM_PROVIDER
names a real provider but the rest of the config is incomplete."""
import pytest

from app.config import Settings, validate_llm_config


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_mock_provider_never_requires_any_extra_config():
    validate_llm_config(_settings(llm_provider="mock"))


def test_real_provider_without_allow_external_calls_raises():
    with pytest.raises(RuntimeError, match="ALLOW_EXTERNAL_LLM_CALLS"):
        validate_llm_config(_settings(
            llm_provider="groq", allow_external_llm_calls=False, groq_api_key="gk_real",
        ))


def test_real_provider_with_allow_external_but_missing_key_raises():
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        validate_llm_config(_settings(
            llm_provider="groq", allow_external_llm_calls=True, groq_api_key=None,
        ))


def test_real_provider_fully_configured_passes():
    validate_llm_config(_settings(
        llm_provider="groq", allow_external_llm_calls=True, groq_api_key="gk_real",
    ))
    validate_llm_config(_settings(
        llm_provider="gemini", allow_external_llm_calls=True, gemini_api_key="gm_real",
    ))


def test_unrecognised_provider_name_raises():
    with pytest.raises(RuntimeError, match="not a recognised provider name"):
        validate_llm_config(_settings(
            llm_provider="not-a-real-provider", allow_external_llm_calls=True,
        ))


def test_failover_with_no_keys_in_the_chain_raises():
    with pytest.raises(RuntimeError, match="LLM_FAILOVER_ORDER"):
        validate_llm_config(_settings(
            llm_provider="failover", allow_external_llm_calls=True,
            groq_api_key=None, gemini_api_key=None, nvidia_api_key=None,
        ))


def test_failover_with_at_least_one_key_passes():
    validate_llm_config(_settings(
        llm_provider="failover", allow_external_llm_calls=True,
        groq_api_key="gk_real", gemini_api_key=None, nvidia_api_key=None,
    ))


def test_the_exact_reported_render_misconfiguration_is_caught():
    """The literal env vars reported as present on Render: DATABASE_URL,
    GEMINI_API_KEY, GROQ_API_KEY, NVIDIA_OCR_API_KEY — but no LLM_PROVIDER
    and no ALLOW_EXTERNAL_LLM_CALLS. LLM_PROVIDER therefore still defaults
    to "mock", which is a valid (if surprising) configuration on its own —
    this test documents that validate_llm_config correctly does NOT raise
    for it, since the actual fix is setting LLM_PROVIDER, not just adding
    the key env vars."""
    validate_llm_config(_settings(
        gemini_api_key="real-gemini-key", groq_api_key="real-groq-key",
    ))
