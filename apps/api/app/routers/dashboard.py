from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.tender import Tender
from app.schemas.schemas import DashboardStats, TenderSummary
from app.services.tender_helpers import active_analysis, to_summary_dict

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    tenders = db.query(Tender).options(joinedload(Tender.analyses)).all()
    scores, high, review, low = [], 0, 0, 0
    for t in tenders:
        active = active_analysis(t)
        if not active or active.final_score is None:
            continue
        scores.append(active.final_score)
        if active.final_recommendation == "PURSUE":
            high += 1
        elif active.final_recommendation == "REVIEW":
            review += 1
        elif active.final_recommendation == "DO_NOT_PURSUE":
            low += 1

    week_ago = datetime.utcnow() - timedelta(days=7)
    new_this_week = sum(1 for t in tenders if t.uploaded_at >= week_ago)
    upcoming = sum(1 for t in tenders if t.submission_deadline)

    return DashboardStats(
        total_opportunities=len(tenders), high_priority=high, review_required=review, low_fit=low,
        new_this_week=new_this_week, average_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
        upcoming_deadlines=upcoming,
    )


@router.get("/opportunities", response_model=list[TenderSummary])
def opportunities(db: Session = Depends(get_db)):
    tenders = db.query(Tender).options(joinedload(Tender.analyses)).order_by(Tender.uploaded_at.desc()).all()
    return [TenderSummary(**to_summary_dict(t)) for t in tenders]
