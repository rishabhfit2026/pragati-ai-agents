import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

# In local dev the repo layout is apps/api/app/config.py -> ../../../knowledge.
# In Docker the knowledge folder is mounted directly at /knowledge (see
# docker/docker-compose.yml) — KNOWLEDGE_DIR env var overrides the default.
_default_knowledge_dir = BASE_DIR.parent.parent.parent / "knowledge"
KNOWLEDGE_DIR = Path(os.environ.get("KNOWLEDGE_DIR", _default_knowledge_dir))

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """All server-side configuration. Never expose secrets to the frontend —
    the web app only ever talks to this API, never to the LLM/OCR providers directly."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Pragati Opportunity Intelligence"
    environment: str = "development"

    database_url: str = f"sqlite:///{DATA_DIR / 'pragati.db'}"

    # LLM provider abstraction. "mock" = deterministic, offline, zero-cost, no API key
    # required. This is the default so the app is runnable out of the box.
    # One of: mock | anthropic | openai | groq | gemini | nvidia | failover
    llm_provider: str = "mock"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    nvidia_api_key: str | None = None
    # Per-provider default model used when LLM_MODEL is not set; each real
    # provider class also has its own sane default, so this only needs to be
    # set when overriding the model for whichever provider is active.
    llm_model: str | None = None
    # LLM_PROVIDER=failover chains these, in order, using whichever of them
    # has an API key configured — a rate limit/outage on one just moves on
    # to the next rather than failing the whole analysis.
    llm_failover_order: tuple[str, ...] = ("groq", "gemini", "nvidia")

    # OCR provider abstraction. "mock" simulates OCR for scanned pages when
    # tesseract is not installed on the host.
    ocr_provider: str = "auto"  # auto | tesseract | mock | nvidia
    nvidia_ocr_api_key: str | None = None

    max_upload_mb: int = 25
    allowed_upload_types: tuple[str, ...] = (".pdf",)

    prompt_version: str = "req-extract-v1"
    scoring_version: str = "score-v1"

    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")

    # If false, no document content (text OR page images) is ever sent to an
    # external LLM/OCR API, regardless of llm_provider/ocr_provider — enforced
    # server-side here, not left to the caller or the frontend.
    allow_external_llm_calls: bool = False


settings = Settings()
