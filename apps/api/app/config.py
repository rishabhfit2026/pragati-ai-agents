import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Local dev default: apps/api/app/data/uploads, inside the source tree. On a
# host with ephemeral local disk (e.g. Render without a persistent disk
# attached), anything written here is lost on every restart/redeploy —
# UPLOAD_DIR env var overrides the default so production can point this at a
# mounted persistent disk instead, with zero change to local dev behavior.
_default_upload_dir = DATA_DIR / "uploads"
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(_default_upload_dir)))

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

    # Exact origins that are always allowed. Local dev only needs localhost
    # here — production/preview Vercel origins are handled unconditionally
    # by cors_origin_regex below, not by this list, so a narrower local .env
    # value (e.g. just localhost) can never accidentally lock out Vercel.
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://pragati-ai-agents.vercel.app",
    )
    # Additionally allow any Vercel preview URL for this project (each deploy
    # gets a new random-hash subdomain, so a fixed list would need editing
    # after every single deploy) — matches both the "-<hash>-<user>" preview
    # pattern and the "-git-<branch>-<user>" branch-deploy pattern.
    cors_origin_regex: str | None = r"^https://pragati-ai-agents(-[a-zA-Z0-9-]+)?\.vercel\.app$"

    @field_validator("cors_origin_regex")
    @classmethod
    def _empty_regex_means_disabled(cls, v: str | None) -> str | None:
        # A regex of "" matches every string (re.match("", anything) is
        # truthy) — if this were ever passed straight to CORSMiddleware, an
        # accidentally-empty CORS_ORIGIN_REGEX env var would silently open
        # CORS to every origin while allow_credentials=True is on. Normalize
        # "empty" to "disabled" instead.
        return v or None

    # If false, no document content (text OR page images) is ever sent to an
    # external LLM/OCR API, regardless of llm_provider/ocr_provider — enforced
    # server-side here, not left to the caller or the frontend.
    allow_external_llm_calls: bool = False


settings = Settings()
