"""Verifies CORSSafeErrorMiddleware (app/error_middleware.py) is a safety net
for TRULY unhandled exceptions only — it must never mask or reword a genuine,
already-meaningful application error (a 404, a validation error, a specific
HTTPException), and it must never silently swallow an unexpected exception
without logging it somewhere an operator would actually see it."""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.error_middleware import CORSSafeErrorMiddleware


def _probe_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CORSSafeErrorMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    class Item(BaseModel):
        name: str
        count: int

    @app.get("/specific-404")
    def specific_404():
        raise HTTPException(404, "Tender xyz not found — this exact message must survive")

    @app.get("/specific-400")
    def specific_400():
        raise HTTPException(400, "Only .pdf files are accepted — this exact message must survive")

    @app.post("/validate")
    def validate(item: Item):
        return {"ok": True, "item": item.model_dump()}

    @app.get("/truly-broken")
    def truly_broken():
        raise RuntimeError("a real, unexpected bug with no handler")

    return app


def test_specific_404_error_message_is_not_replaced_by_generic_text():
    client = TestClient(_probe_app())
    resp = client.get("/specific-404")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Tender xyz not found — this exact message must survive"


def test_specific_400_error_message_is_not_replaced_by_generic_text():
    client = TestClient(_probe_app())
    resp = client.get("/specific-400")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Only .pdf files are accepted — this exact message must survive"


def test_valid_request_body_passes_through_untouched():
    client = TestClient(_probe_app())
    resp = client.post("/validate", json={"name": "helmet-flagship", "count": 3})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "item": {"name": "helmet-flagship", "count": 3}}


def test_pydantic_validation_error_is_not_swallowed_or_reworded():
    """A 422 from FastAPI's own request-validation is a specific, already-
    handled exception type (RequestValidationError) — must reach the client
    with its real validation detail, not the generic 500 fallback text."""
    client = TestClient(_probe_app())
    resp = client.post("/validate", json={"name": "helmet-flagship"})  # missing required "count"
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body
    assert any("count" in str(err.get("loc", "")) for err in body["detail"])


def test_truly_unhandled_exception_is_logged_with_full_traceback(caplog):
    """The one thing the middleware SHOULD replace with a generic message is
    a genuinely unexpected exception — but it must still be fully logged
    (traceback and all) so an operator can actually diagnose it, not just a
    silent 500 that vanishes into nothing."""
    client = TestClient(_probe_app(), raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="app.error_middleware"):
        resp = client.get("/truly-broken")

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Internal server error. This has been logged."
    # The real error must be findable in the logs, not lost.
    assert any("RuntimeError" in r.getMessage() or "a real, unexpected bug" in r.getMessage() for r in caplog.records) \
        or any(r.exc_info and issubclass(r.exc_info[0], RuntimeError) for r in caplog.records)
