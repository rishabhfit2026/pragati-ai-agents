from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app import models  # noqa: F401  ensures models are registered before create_all
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
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
