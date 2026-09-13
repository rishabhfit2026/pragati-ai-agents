"""Real LLM provider using Groq's OpenAI-compatible Chat Completions API
(fast Llama/GPT-OSS/Kimi inference). Only ever instantiated server-side, only
when explicitly enabled via ALLOW_EXTERNAL_LLM_CALLS=true and a GROQ_API_KEY
is present (app/llm/provider.py enforces this gate)."""
from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    base_url = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, model: str = "openai/gpt-oss-120b", api_key: str | None = None):
        from app.config import settings

        super().__init__(api_key=api_key or settings.groq_api_key or "", model=model)
