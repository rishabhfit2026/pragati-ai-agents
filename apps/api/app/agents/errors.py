"""Shared agent exception types used by the orchestrator's retry/fallback logic
and by the developer-mode failure simulator (section 21)."""


class ToolError(Exception):
    """Simulates a downstream tool/dependency failure (e.g. knowledge base unreachable)."""
