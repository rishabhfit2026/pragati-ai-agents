from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app import models  # noqa: F401  ensures models are registered before create_all
from app.error_middleware import CORSSafeErrorMiddleware
from app.routers import agents, dashboard, demo, knowledge, search, tenders

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description=(
        "Prototype AI Tender Intelligence & Bid Decision System for Pragati Defence Systems. "
        "Uses only publicly available Pragati information and clearly-labelled synthetic demo data — "
        "no confidential/internal Pragati data is used."
    ),
    version="0.1.0",
)

# Order matters here: Starlette's add_middleware() prepends, so whichever
# middleware is added FIRST ends up INNERMOST (closest to the router) and
# whichever is added LAST ends up OUTERMOST (closest to the client). The
# error-catching middleware must be added BEFORE CORSMiddleware so it sits
# inside CORS's wrapping — that way, when it catches an unhandled exception
# and builds a fallback response, that response still flows back out through
# CORSMiddleware and gets Access-Control-Allow-Origin applied. Added the
# other way around, error responses would come from Starlette's built-in
# ServerErrorMiddleware (which always sits outside every user middleware)
# and would be missing CORS headers entirely — verified empirically; a bare
# @app.exception_handler(Exception) does NOT fix this, see error_middleware.py.
app.add_middleware(CORSSafeErrorMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenders.router)
app.include_router(dashboard.router)
app.include_router(agents.router)
app.include_router(knowledge.router)
app.include_router(search.router)
app.include_router(demo.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
