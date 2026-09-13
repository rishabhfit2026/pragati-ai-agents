"""Real LLM provider using the OpenAI Chat Completions API. Only ever
instantiated server-side, only when explicitly enabled via
ALLOW_EXTERNAL_LLM_CALLS=true and an OPENAI_API_KEY is present."""
from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    base_url = "https://api.openai.com/v1/chat/completions"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        from app.config import settings

        super().__init__(api_key=api_key or settings.openai_api_key or "", model=model)
