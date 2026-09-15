from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session, joinedload

from app.agents.orchestrator import run_pipeline
from app.config import settings, UPLOAD_DIR
from app.db import get_db
from app.models.analysis import Analysis
from app.models.tender import Tender
from app.schemas.schemas import (
    TenderSummary, TenderDetail, AnalysisOut, AnalyzeRequest, ReplayRequest, ReplayComparison,
    DecisionOverrideRequest,
)
from app.services.audit import log_event
from app.services.diff import diff_analyses
from app.services.report import render_html_report, render_pdf_report
from app.services.serialize import analysis_to_dict, tender_to_dict
from app.services.tender_helpers import get_tender as _get_tender, active_analysis as _active_analysis, to_summary_dict as _to_summary

router = APIRouter(prefix="/api/tenders", tags=["tenders"])


@router.post("/upload", response_model=TenderDetail)
async def upload_tender(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in settings.allowed_upload_types):
        raise HTTPException(400, f"Only {settings.allowed_upload_types} files are accepted")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File exceeds {settings.max_upload_mb}MB limit")
    if not content.startswith(b"%PDF"):
        raise HTTPException(400, "File does not appear to be a valid PDF")

    file_hash = hashlib.sha256(content).hexdigest()
    stored_name = f"{uuid.uuid4().hex[:12]}_{Path(file.filename).name}"
    dest = UPLOAD_DIR / stored_name
    dest.write_bytes(content)

    tender = Tender(
        filename=file.filename, file_path=str(dest), file_hash=file_hash, file_size_bytes=len(content),
    )
    db.add(tender)
    db.flush()
    log_event(db, tender_id=tender.id, event_type="DOCUMENT_UPLOADED",
              description=f"Document '{file.filename}' uploaded ({len(content)} bytes, sha256={file_hash[:12]}...).")
    db.commit()
    db.refresh(tender)
    return TenderDetail(**_to_summary(tender))


@router.post("/{tender_id}/analyze", response_model=AnalysisOut)
def analyze_tender(tender_id: str, req: AnalyzeRequest = AnalyzeRequest(), db: Session = Depends(get_db)):
    tender = _get_tender(db, tender_id)
    try:
        file_bytes = Path(tender.file_path).read_bytes()
    except OSError as e:
        # Deliberately its own try/except, separate from the pipeline's
        # below: this file read used to happen BEFORE the try block, so a
        # missing file (e.g. ephemeral disk storage on a host like Render —
        # an uploaded file doesn't survive a restart/redeploy unless a
        # persistent disk is attached) raised an unhandled OSError that
        # bypassed FastAPI's exception handling entirely and, as a direct
        # consequence, was missing CORS response headers — which a browser
        # reports as a CORS error, hiding the real cause. Every failure path
        # in this endpoint must resolve to an HTTPException.
        raise HTTPException(
            404,
            f"The uploaded document for this tender could not be found on the server ({e}). "
            "It may have been lost due to a server restart — please re-upload the tender and try again.",
        )
    try:
        analysis = run_pipeline(db, tender, file_bytes, simulate_failure=req.simulate_failure)
        db.commit()
    except Exception as e:
        # run_pipeline's own except block already rolled back the failed
        # transaction and flushed a fresh FAILED Analysis/AuditEvent record
        # in a clean one (see orchestrator.py) — this just needs to make
        # that durable. Still guarded with its own rollback-on-failure:
        # committing again without checking for a further failure is exactly
        # the bug this whole pattern exists to avoid repeating — a Postgres
        # transaction that failed once rejects every further command until
        # it's explicitly rolled back, so an unguarded second commit() would
        # itself raise a second, more confusing error that masks the first.
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(500, f"Analysis failed: {e}")
    db.refresh(analysis)
    return AnalysisOut(**analysis_to_dict(analysis))


@router.get("", response_model=list[TenderSummary])
def list_tenders(db: Session = Depends(get_db)):
    tenders = db.query(Tender).options(joinedload(Tender.analyses)).order_by(Tender.uploaded_at.desc()).all()
    return [TenderSummary(**_to_summary(t)) for t in tenders]


@router.get("/{tender_id}", response_model=TenderDetail)
def get_tender(tender_id: str, db: Session = Depends(get_db)):
    tender = _get_tender(db, tender_id)
    return TenderDetail(**_to_summary(tender))


def _get_analysis(db: Session, tender_id: str, analysis_id: str | None = None) -> Analysis:
    tender = _get_tender(db, tender_id)
    if analysis_id:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.tender_id == tender_id).first()
    else:
        analysis = _active_analysis(tender)
    if not analysis:
        raise HTTPException(404, "No analysis found for this tender. Run /analyze first.")
    return analysis


@router.get("/{tender_id}/analyses", response_model=list[AnalysisOut])
def list_analyses(tender_id: str, db: Session = Depends(get_db)):
    tender = _get_tender(db, tender_id)
    return [AnalysisOut(**analysis_to_dict(a)) for a in tender.analyses]


@router.get("/{tender_id}/analysis", response_model=AnalysisOut)
def get_active_analysis(tender_id: str, analysis_id: str | None = None, db: Session = Depends(get_db)):
    analysis = _get_analysis(db, tender_id, analysis_id)
    return AnalysisOut(**analysis_to_dict(analysis))


@router.get("/{tender_id}/requirements")
def get_requirements(tender_id: str, analysis_id: str | None = None, db: Session = Depends(get_db)):
    analysis = _get_analysis(db, tender_id, analysis_id)
    return analysis_to_dict(analysis)["requirements"]


@router.get("/{tender_id}/compliance")
def get_compliance(tender_id: str, analysis_id: str | None = None, db: Session = Depends(get_db)):
    analysis = _get_analysis(db, tender_id, analysis_id)
    return analysis_to_dict(analysis)["compliance_items"]


@router.get("/{tender_id}/risks")
def get_risks(tender_id: str, analysis_id: str | None = None, db: Session = Depends(get_db)):
    analysis = _get_analysis(db, tender_id, analysis_id)
    return analysis_to_dict(analysis)["risks"]


@router.get("/{tender_id}/score")
def get_score(tender_id: str, analysis_id: str | None = None, db: Session = Depends(get_db)):
    analysis = _get_analysis(db, tender_id, analysis_id)
    return analysis_to_dict(analysis)["score"]


@router.get("/{tender_id}/timeline")
def get_timeline(tender_id: str, db: Session = Depends(get_db)):
    tender = _get_tender(db, tender_id)
    return [
        {
            "id": e.id, "timestamp": e.timestamp, "event_type": e.event_type, "description": e.description,
            "actor": e.actor, "analysis_id": e.analysis_id, "metadata": e.event_metadata,
        }
        for e in sorted(tender.audit_events, key=lambda e: e.timestamp)
    ]


@router.post("/{tender_id}/decision", response_model=AnalysisOut)
def override_decision(tender_id: str, body: DecisionOverrideRequest, db: Session = Depends(get_db)):
    from datetime import datetime

    analysis = _get_analysis(db, tender_id, None)
    previous = analysis.final_recommendation
    analysis.final_recommendation = body.final_recommendation
    analysis.human_override = True
    analysis.override_reason = body.reason
    analysis.overridden_by = body.actor
    analysis.overridden_at = datetime.utcnow()
    db.flush()
    log_event(
        db, tender_id=tender_id, analysis_id=analysis.id, event_type="HUMAN_OVERRIDE", actor=body.actor,
        description=f"Human override: AI recommended {analysis.ai_recommendation}, human set {body.final_recommendation}. Reason: {body.reason}",
        metadata={"previous": previous, "new": body.final_recommendation, "reason": body.reason},
    )
    db.commit()
    db.refresh(analysis)
    return AnalysisOut(**analysis_to_dict(analysis))


@router.post("/{tender_id}/replay", response_model=ReplayComparison)
def replay_analysis(tender_id: str, req: ReplayRequest, db: Session = Depends(get_db)):
    tender = _get_tender(db, tender_id)
    old_analysis = _active_analysis(tender)
    if not old_analysis:
        raise HTTPException(404, "No prior analysis to replay. Run /analyze first.")
    old_dict = analysis_to_dict(old_analysis)

    try:
        file_bytes = Path(tender.file_path).read_bytes()
    except OSError as e:
        raise HTTPException(
            404,
            f"The uploaded document for this tender could not be found on the server ({e}). "
            "It may have been lost due to a server restart — please re-upload the tender and try again.",
        )
    try:
        new_analysis = run_pipeline(
            db, tender, file_bytes,
            llm_provider_name=req.llm_provider, llm_model=req.llm_model,
            prompt_version=req.prompt_version, scoring_version=req.scoring_version,
            is_replay_of=old_analysis.id,
        )
        db.commit()
    except Exception as e:
        # Same failure -> retry -> fallback story as /analyze (see the
        # comment there): run_pipeline already rolled back and flushed a
        # clean FAILED record on its own failure, this just persists it.
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(500, f"Replay failed: {e}")
    db.refresh(new_analysis)
    new_dict = analysis_to_dict(new_analysis)

    return ReplayComparison(
        old_analysis=AnalysisOut(**old_dict), new_analysis=AnalysisOut(**new_dict),
        diff=diff_analyses(old_dict, new_dict),
    )


@router.get("/{tender_id}/report.html", response_class=HTMLResponse)
def report_html(tender_id: str, analysis_id: str | None = None, db: Session = Depends(get_db)):
    tender = _get_tender(db, tender_id)
    analysis = _get_analysis(db, tender_id, analysis_id)
    html = render_html_report(tender_to_dict(tender), analysis_to_dict(analysis))
    return HTMLResponse(content=html)


@router.get("/{tender_id}/report.pdf")
def report_pdf(tender_id: str, analysis_id: str | None = None, db: Session = Depends(get_db)):
    tender = _get_tender(db, tender_id)
    analysis = _get_analysis(db, tender_id, analysis_id)
    pdf_bytes = render_pdf_report(tender_to_dict(tender), analysis_to_dict(analysis))
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="opportunity_report_{tender_id}.pdf"'},
    )
