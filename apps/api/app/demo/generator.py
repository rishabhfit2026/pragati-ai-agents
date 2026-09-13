"""Seeds the demo dataset (section 29/30): synthetic PDFs are generated,
uploaded through the same code path as a real upload, analyzed through the
full agent pipeline, and one tender is additionally replayed with a different
scoring configuration so the Replay feature has something to show immediately."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.agents.orchestrator import run_pipeline
from app.config import UPLOAD_DIR
from app.demo.tenders_data import DEMO_TENDERS
from app.models.analysis import AgentRun, Analysis, AuditEvent, CapabilityMatch, ComplianceItem, Requirement, Risk
from app.models.tender import Tender
from app.services.audit import log_event
from app.services.pdf_builder import build_tender_pdf

# Which demo tenders get a deliberately-injected failure on their initial
# analysis, to populate the Agent Run / Audit Timeline with a real
# failure -> retry -> fallback -> success story (section 21/29).
SIMULATED_FAILURES = {
    "vest-capf": "OCR_TIMEOUT",
    "counter-drone-mod": "INVALID_JSON",
}

REPLAY_KEY = "helmet-flagship"


def clear_demo_data(db: Session) -> None:
    demo_tenders = db.query(Tender).filter(Tender.is_demo.is_(True)).all()
    for t in demo_tenders:
        db.query(AgentRun).filter(AgentRun.analysis_id.in_(
            db.query(Analysis.id).filter(Analysis.tender_id == t.id)
        )).delete(synchronize_session=False)
        db.query(CapabilityMatch).filter(CapabilityMatch.analysis_id.in_(
            db.query(Analysis.id).filter(Analysis.tender_id == t.id)
        )).delete(synchronize_session=False)
        db.query(ComplianceItem).filter(ComplianceItem.analysis_id.in_(
            db.query(Analysis.id).filter(Analysis.tender_id == t.id)
        )).delete(synchronize_session=False)
        db.query(Risk).filter(Risk.analysis_id.in_(
            db.query(Analysis.id).filter(Analysis.tender_id == t.id)
        )).delete(synchronize_session=False)
        db.query(Requirement).filter(Requirement.analysis_id.in_(
            db.query(Analysis.id).filter(Analysis.tender_id == t.id)
        )).delete(synchronize_session=False)
        db.query(Analysis).filter(Analysis.tender_id == t.id).delete(synchronize_session=False)
        db.query(AuditEvent).filter(AuditEvent.tender_id == t.id).delete(synchronize_session=False)
        db.delete(t)
    db.commit()


def load_demo_data(db: Session) -> dict:
    clear_demo_data(db)
    created = []

    for entry in DEMO_TENDERS:
        pdf_bytes = build_tender_pdf(entry["meta"], entry["sections"])
        stored_name = f"demo_{entry['key']}_{uuid.uuid4().hex[:8]}.pdf"
        dest = UPLOAD_DIR / stored_name
        dest.write_bytes(pdf_bytes)

        import hashlib
        tender = Tender(
            filename=f"{entry['key']}.pdf", file_path=str(dest),
            file_hash=hashlib.sha256(pdf_bytes).hexdigest(), file_size_bytes=len(pdf_bytes), is_demo=True,
        )
        db.add(tender)
        db.flush()
        log_event(db, tender_id=tender.id, event_type="DOCUMENT_UPLOADED",
                  description=f"[DEMO DATA] Synthetic tender '{entry['meta']['title']}' loaded.")

        simulate_failure = SIMULATED_FAILURES.get(entry["key"])
        analysis = run_pipeline(db, tender, pdf_bytes, simulate_failure=simulate_failure)
        db.commit()

        if entry["key"] == REPLAY_KEY:
            db.refresh(tender)
            run_pipeline(
                db, tender, pdf_bytes, scoring_version="score-v2", is_replay_of=analysis.id,
            )
            db.commit()

        created.append(entry["key"])

    return {"loaded": created, "count": len(created)}
