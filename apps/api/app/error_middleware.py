"""Last-resort exception safety net.

Why this exists: Starlette's own `@app.exception_handler(Exception)` does NOT
protect CORS headers on error responses. `Starlette.build_middleware_stack()`
special-cases handlers registered for `Exception` or status `500` — it pulls
them out and hands them to `ServerErrorMiddleware`, which sits OUTSIDE every
user-added middleware including CORSMiddleware:

    ServerErrorMiddleware -> [CORSMiddleware, ...] -> ExceptionMiddleware -> Router

Any exception with no *specific* registered handler (e.g. a bare
FileNotFoundError from a missing upload, a DB error, anything unforeseen)
escapes ExceptionMiddleware, is caught only by ServerErrorMiddleware, and
that response is built with the ORIGINAL un-wrapped `send` — CORSMiddleware
never gets a chance to add `Access-Control-Allow-Origin`. The browser then
reports this as a generic CORS failure, hiding the real 500 underneath it.
(Verified empirically, not from memory — see the investigation notes in the
PR/commit that added this file.)

The fix is this plain ASGI middleware, added to the app BEFORE CORSMiddleware
in main.py. Starlette's `add_middleware()` prepends each call, so the
middleware added earliest ends up closest to the router (innermost) — that
positions this middleware's try/except INSIDE CORSMiddleware's wrapping, so
whatever response it builds still flows back out through CORSMiddleware and
gets the header applied. This is a safety net only: known failure paths
(e.g. a missing uploaded file) should still be turned into a proper
HTTPException at the point they occur, since that gives the caller a useful
error message instead of a generic "Internal Server Error".
"""
from __future__ import annotations

import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class CORSSafeErrorMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: dict) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("Unhandled exception in request pipeline")
            if response_started:
                # Headers (and possibly body) already went out — sending a
                # fresh response now would violate the ASGI protocol. Nothing
                # safe to do but let it propagate; this only matters for
                # streaming responses, which this app doesn't use.
                raise
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error. This has been logged."},
            )
            await response(scope, receive, send)
