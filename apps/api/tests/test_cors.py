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


VERCEL_ORIGIN = "https://pragati-ai-agents.vercel.app"


def _sample_pdf_bytes() -> bytes:
    from app.demo.tenders_data import DEMO_TENDERS
    from app.services.pdf_builder import build_tender_pdf

    entry = next(e for e in DEMO_TENDERS if e["key"] == "helmet-flagship")
    return build_tender_pdf(entry["meta"], entry["sections"])


def test_analyze_preflight_from_vercel_origin(client):
    """A real browser sends this OPTIONS preflight before the actual POST
    whenever the request has a JSON body — this must be answered correctly
    for the frontend's analyze button to work at all. Preflight is handled
    entirely inside CORSMiddleware (it never reaches routing), so a
    non-existent tender id is fine here — only the CORS negotiation itself
    is under test."""
    resp = client.options(
        "/api/tenders/does-not-exist/analyze",
        headers={
            "Origin": VERCEL_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == VERCEL_ORIGIN
    assert "POST" in resp.headers.get("access-control-allow-methods", "")
    assert "content-type" in resp.headers.get("access-control-allow-headers", "").lower()
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_analyze_success_response_includes_cors_headers(client):
    """The actual POST, not just the preflight — a successful analysis must
    carry the CORS header too, or the browser discards the (perfectly fine)
    response anyway."""
    pdf_bytes = _sample_pdf_bytes()
    upload_resp = client.post("/api/tenders/upload", files={"file": ("tender.pdf", pdf_bytes, "application/pdf")})
    tender_id = upload_resp.json()["id"]

    resp = client.post(f"/api/tenders/{tender_id}/analyze", json={}, headers={"Origin": VERCEL_ORIGIN})

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == VERCEL_ORIGIN


def test_analyze_missing_uploaded_file_still_returns_cors_headers(client):
    """Reproduces the exact deployed bug: the tender row exists in the DB,
    but its uploaded PDF is gone from disk (e.g. Render's ephemeral storage
    after a restart/redeploy — ordinary and expected there without a
    persistent disk attached). Before the fix, Path.read_bytes() ran BEFORE
    the endpoint's try/except, so the resulting OSError was a genuinely
    unhandled exception: it skipped FastAPI's exception handling entirely,
    which meant the response came from Starlette's ServerErrorMiddleware —
    the one middleware layer that sits OUTSIDE CORSMiddleware — so it had no
    Access-Control-Allow-Origin header at all. A browser reports that as a
    bare CORS failure, which is exactly what was observed, even though the
    real cause was an ordinary missing file. This must now come back as a
    clean 404 with CORS headers intact."""
    import os

    from app.db import SessionLocal
    from app.models.tender import Tender

    pdf_bytes = _sample_pdf_bytes()
    upload_resp = client.post("/api/tenders/upload", files={"file": ("tender.pdf", pdf_bytes, "application/pdf")})
    tender_id = upload_resp.json()["id"]

    db = SessionLocal()
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    os.remove(tender.file_path)
    db.close()

    resp = client.post(f"/api/tenders/{tender_id}/analyze", json={}, headers={"Origin": VERCEL_ORIGIN})

    assert resp.status_code == 404
    assert resp.headers.get("access-control-allow-origin") == VERCEL_ORIGIN


def test_unhandled_exception_anywhere_still_returns_cors_headers():
    """Defense-in-depth check for CORSSafeErrorMiddleware directly, isolated
    from any specific route: an exception type nobody registered a handler
    for must still come back with CORS headers intact. Built as a minimal
    app replicating main.py's exact middleware setup and ordering, rather
    than monkeypatching a route on the real `client` fixture's app — a
    FastAPI route decorator captures its handler by reference at import
    time, so patching the module attribute afterwards wouldn't actually
    change what the already-registered route calls."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    from app.error_middleware import CORSSafeErrorMiddleware

    probe_app = FastAPI()
    probe_app.add_middleware(CORSSafeErrorMiddleware)
    probe_app.add_middleware(
        CORSMiddleware, allow_origins=[VERCEL_ORIGIN], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

    @probe_app.get("/boom")
    def boom():
        raise RuntimeError("totally unexpected failure, no handler registered anywhere")

    probe_client = TestClient(probe_app, raise_server_exceptions=False)
    resp = probe_client.get("/boom", headers={"Origin": VERCEL_ORIGIN})

    assert resp.status_code == 500
    assert resp.headers.get("access-control-allow-origin") == VERCEL_ORIGIN
