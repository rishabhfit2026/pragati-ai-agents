"""Real LLM provider using Google's Gemini API via its OpenAI-compatible
endpoint. Only ever instantiated server-side, only when explicitly enabled
via ALLOW_EXTERNAL_LLM_CALLS=true and a GEMINI_API_KEY is present."""
from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleProvider


class GeminiProvider(OpenAICompatibleProvider):
    name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str | None = None):
        from app.config import settings

        super().__init__(api_key=api_key or settings.gemini_api_key or "", model=model)
