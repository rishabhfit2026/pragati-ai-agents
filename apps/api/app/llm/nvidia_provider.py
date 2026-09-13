"""Real LLM provider using NVIDIA NIM's OpenAI-compatible Chat Completions API
(build.nvidia.com — hosted open models like Llama/Nemotron). Only ever
instantiated server-side, only when explicitly enabled via
ALLOW_EXTERNAL_LLM_CALLS=true and an NVIDIA_API_KEY is present. JSON mode
support varies by model on NIM, so this provider does not request it and
instead relies on the base class's fenced-code-block-tolerant JSON parsing."""
from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleProvider


class NvidiaProvider(OpenAICompatibleProvider):
    name = "nvidia"
    base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    supports_json_mode = False

    def __init__(self, model: str = "nvidia/llama-3.1-nemotron-70b-instruct", api_key: str | None = None):
        from app.config import settings

        super().__init__(api_key=api_key or settings.nvidia_api_key or "", model=model)
