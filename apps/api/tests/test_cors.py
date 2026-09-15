"""CORS configuration tests — verifies the Vercel origin regex + exact-match
list wired into CORSMiddleware (app/main.py) behave correctly against the
real app, not just the compiled pattern in isolation.

Starlette's CORSMiddleware always returns 200 for a simple request regardless
of origin — the actual enforcement signal a browser (and this test) checks is
whether the `access-control-allow-origin` response header is present."""


def _allowed_origin(client, origin: str) -> bool:
    resp = client.get("/api/health", headers={"Origin": origin})
    assert resp.status_code == 200
    return resp.headers.get("access-control-allow-origin") == origin


def test_production_vercel_url_is_allowed(client):
    assert _allowed_origin(client, "https://pragati-ai-agents.vercel.app")


def test_vercel_preview_url_is_allowed(client):
    # A realistic Vercel preview deployment URL (random hash + user slug) —
    # this must work without ever hardcoding this exact hash anywhere.
    assert _allowed_origin(client, "https://pragati-ai-agents-g9u5fir6-ri-shabh2.vercel.app")


def test_vercel_git_branch_deploy_url_is_allowed(client):
    assert _allowed_origin(client, "https://pragati-ai-agents-git-main-rishabh.vercel.app")


def test_localhost_is_allowed_for_local_dev(client):
    assert _allowed_origin(client, "http://localhost:3000")
    assert _allowed_origin(client, "http://127.0.0.1:3000")


def test_lookalike_prefixed_domain_is_rejected(client):
    assert not _allowed_origin(client, "https://evil-pragati-ai-agents.vercel.app")


def test_domain_suffix_attack_is_rejected(client):
    # "pragati-ai-agents.vercel.app" as a PREFIX of a domain the attacker
    # actually controls — must not be treated as a subdomain match.
    assert not _allowed_origin(client, "https://pragati-ai-agents.vercel.app.evil.com")


def test_unrelated_domain_is_rejected(client):
    assert not _allowed_origin(client, "https://totally-unrelated-site.com")


def test_empty_cors_origin_regex_env_var_is_treated_as_disabled_not_wildcard():
    """Regression test for a real vulnerability found while reviewing this
    config: re.match("", anything) is truthy, so a blank CORS_ORIGIN_REGEX
    env var must never be passed to CORSMiddleware as-is — that would match
    every origin while allow_credentials=True is on."""
    from app.config import Settings

    s = Settings(cors_origin_regex="")
    assert s.cors_origin_regex is None
