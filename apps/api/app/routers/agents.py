"""Agent Observability — section 19/28: GET /api/agents/runs"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.analysis import AgentRun, Analysis
from app.schemas.schemas import AgentRunOut

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/runs")
def list_agent_runs(tender_id: str | None = None, analysis_id: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(AgentRun).join(Analysis, AgentRun.analysis_id == Analysis.id)
    if analysis_id:
        q = q.filter(AgentRun.analysis_id == analysis_id)
    if tender_id:
        q = q.filter(Analysis.tender_id == tender_id)
    runs = q.order_by(AgentRun.started_at.desc()).limit(limit).all()
    return [
        {**AgentRunOut.model_validate(r).model_dump(), "analysis_id": r.analysis_id, "tender_id": r.analysis.tender_id}
        for r in runs
    ]
