from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.analysis import Analysis
from app.models.tender import Tender
from app.services.serialize import fit_label, risk_label, tender_to_dict


def get_tender(db: Session, tender_id: str) -> Tender:
    tender = db.query(Tender).options(joinedload(Tender.analyses)).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(404, "Tender not found")
    return tender


def active_analysis(tender: Tender) -> Analysis | None:
    if tender.active_analysis_id:
        for a in tender.analyses:
            if a.id == tender.active_analysis_id:
                return a
    return tender.analyses[-1] if tender.analyses else None


def to_summary_dict(tender: Tender) -> dict:
    active = active_analysis(tender)
    d = tender_to_dict(tender)
    d.update({
        "uploaded_at": tender.uploaded_at,
        "final_score": active.final_score if active else None,
        "final_recommendation": active.final_recommendation if active else None,
        "fit_label": fit_label(active.final_score if active else None),
        "risk_label": risk_label(active),
        "active_analysis_id": tender.active_analysis_id,
    })
    return d
