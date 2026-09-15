"""Regression tests for the production bug: tenders.issue_date /
.submission_deadline / .delivery_deadline were VARCHAR(32), and a real
tender's delivery_deadline ("12 months from date of contract signing", 39
chars) exceeded it, causing psycopg2.errors.StringDataRightTruncation on
Render — which then cascaded into a second, more confusing failure because
the code attempted further DB operations without rolling back first.

SQLite (this project's default test DB) does NOT enforce VARCHAR length at
all, so it cannot itself reproduce the original crash — these tests are
split into two tiers accordingly:
  1. Portable tests that run everywhere (model column lengths, and the full
     pipeline preserving the value in full against SQLite).
  2. A real-Postgres test that reproduces the ACTUAL failure mode and its
     recovery, auto-skipped if no Postgres is reachable (set
     TEST_POSTGRES_URL to run it; see the module below).
"""
from __future__ import annotations

import os

import pytest

# The exact values from the reported Render error.
REAL_VALUES = {
    "title": "Procurement of Ballistic Combat Helmets for Infantry",
    "issuing_organization": "Indian Army - Directorate of Ordnance",
    "tender_number": "IA/ORD/2026/HEL-014",
    "issue_date": "02 Aug 2026",
    "submission_deadline": "10 Oct 2026",
    "delivery_deadline": "12 months from date of contract signing",
    "geography": "Pan-India, consignee depots as per Annexure A",
    "estimated_quantity": "12,000 units",
    "product_category": "Combat Helmet",
}


def test_delivery_deadline_real_value_is_39_characters():
    # Sanity-anchor for the whole test module: if this value's length ever
    # changes (e.g. someone "fixes" the fixture), the rest of these tests
    # would silently stop meaning what they claim to.
    assert len(REAL_VALUES["delivery_deadline"]) == 39


@pytest.mark.parametrize("field", ["issue_date", "submission_deadline", "delivery_deadline"])
def test_widened_columns_fit_the_real_reported_values(field):
    from app.models.tender import Tender

    column = Tender.__table__.columns[field]
    value = REAL_VALUES[field]
    assert column.type.length is not None
    assert column.type.length >= len(value), (
        f"{field} column length ({column.type.length}) is too short for the real "
        f"reported value ({len(value)} chars) — this is exactly the bug that broke "
        f"analysis on Render."
    )
    # Also guard the previously-broken 32-char limit specifically: this must
    # never regress back down to a value this small.
    assert column.type.length > 32


def test_unrelated_metadata_columns_were_not_narrowed():
    """This fix must only widen the three date/deadline columns — it must
    not accidentally shrink anything else."""
    from app.models.tender import Tender

    cols = Tender.__table__.columns
    assert cols["title"].type.length == 512
    assert cols["issuing_organization"].type.length == 256
    assert cols["tender_number"].type.length == 128
    assert cols["geography"].type.length == 128
    assert cols["estimated_quantity"].type.length == 128
    assert cols["product_category"].type.length == 128


def test_full_pipeline_stores_real_long_delivery_deadline_untruncated(client, monkeypatch):
    """End-to-end (against the default SQLite test DB): the exact reported
    tender metadata flows through upload -> analyze and is stored in full,
    not truncated to a shorter value. SQLite won't itself enforce a length
    limit, so this proves the APPLICATION correctly preserves the complete
    value (never truncates it deliberately) — the Postgres-specific
    constraint-enforcement side of this bug is covered separately below."""
    import app.agents.requirement_extraction as req_extraction_module

    original_run = req_extraction_module.run

    def patched_run(document, llm, *, simulate_failure=None):
        result = original_run(document, llm, simulate_failure=simulate_failure)
        result.metadata.update(REAL_VALUES)
        return result

    monkeypatch.setattr(req_extraction_module, "run", patched_run)
    monkeypatch.setattr("app.agents.orchestrator.extract_requirements", patched_run)

    from app.demo.tenders_data import DEMO_TENDERS
    from app.services.pdf_builder import build_tender_pdf

    entry = next(e for e in DEMO_TENDERS if e["key"] == "helmet-flagship")
    pdf_bytes = build_tender_pdf(entry["meta"], entry["sections"])

    upload_resp = client.post("/api/tenders/upload", files={"file": ("tender.pdf", pdf_bytes, "application/pdf")})
    assert upload_resp.status_code == 200
    tender_id = upload_resp.json()["id"]

    analyze_resp = client.post(f"/api/tenders/{tender_id}/analyze", json={})
    assert analyze_resp.status_code == 200

    tender_resp = client.get(f"/api/tenders/{tender_id}")
    assert tender_resp.status_code == 200
    body = tender_resp.json()
    for field, expected in REAL_VALUES.items():
        assert body[field] == expected, f"{field} was altered/truncated: got {body[field]!r}"


# --- Real-Postgres tier: reproduces the actual constraint-enforcement bug ---

TEST_POSTGRES_URL = os.environ.get(
    "TEST_POSTGRES_URL", "postgresql+psycopg2://postgres:test@localhost:15432/pragati_test"
)


def _postgres_available() -> bool:
    try:
        import psycopg2

        conn = psycopg2.connect(TEST_POSTGRES_URL.replace("postgresql+psycopg2://", "postgresql://"))
        conn.close()
        return True
    except Exception:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_available(),
    reason="No reachable Postgres at TEST_POSTGRES_URL — this test reproduces a Postgres-specific "
           "constraint (SQLite doesn't enforce VARCHAR length, so it can't exercise this bug).",
)


@pytest.fixture()
def postgres_session():
    """A real Postgres-backed SQLAlchemy session, schema created fresh from
    the CURRENT models (i.e. already includes this fix) — used to prove the
    real reported values round-trip correctly against a real Postgres
    column-length constraint, not just SQLite's lack of one."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db import Base
    from app import models  # noqa: F401  registers all models on Base.metadata

    engine = create_engine(TEST_POSTGRES_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@requires_postgres
def test_real_reported_values_persist_against_real_postgres(postgres_session):
    """The literal query and values from the Render error report, run
    against a real Postgres database with the fixed schema."""
    from app.models.tender import Tender

    tender = Tender(filename="t.pdf", file_path="/tmp/t.pdf", file_hash="x" * 64)
    postgres_session.add(tender)
    postgres_session.flush()

    for field, value in REAL_VALUES.items():
        setattr(tender, field, value)
    tender.page_count = 2
    postgres_session.commit()  # this exact commit is what raised StringDataRightTruncation before the fix

    postgres_session.refresh(tender)
    for field, value in REAL_VALUES.items():
        assert getattr(tender, field) == value


@requires_postgres
def test_orchestrator_rollback_recovers_cleanly_from_a_real_db_error(postgres_session, monkeypatch):
    """Reproduces the exception-handling bug directly: forces a genuine
    Postgres column-length violation mid-pipeline (title too long — a
    column this fix deliberately did NOT widen, so this remains a real,
    live failure mode) and verifies run_pipeline's except block recovers
    with a single rollback rather than cascading into a second, masking
    exception. Before the fix, the log_event()/db.flush() calls in that
    except block would themselves raise psycopg2.errors.InFailedSqlTransaction
    because the failed statement had left the whole transaction aborted."""
    from app.agents.orchestrator import run_pipeline
    from app.demo.tenders_data import DEMO_TENDERS
    from app.services.pdf_builder import build_tender_pdf
    from app.models.tender import Tender
    from app.models.analysis import Analysis

    entry = next(e for e in DEMO_TENDERS if e["key"] == "helmet-flagship")
    pdf_bytes = build_tender_pdf(entry["meta"], entry["sections"])

    tender = Tender(filename="t.pdf", file_path="/tmp/t.pdf", file_hash="y" * 64)
    postgres_session.add(tender)
    postgres_session.commit()

    class OversizedTitleLLM:
        name = "fake"
        model = "fake-model"
        supports_generic_completion = False

        def extract_tender_metadata(self, pages):
            return {"title": "X" * 600}  # title column is String(512) — still genuinely too long

        def extract_requirements(self, pages):
            return [{"description": "A requirement.", "category": "technical", "mandatory": True,
                      "confidence": 0.8, "source_page": 1, "source_section": None, "source_text_snippet": "A requirement."}]

    monkeypatch.setattr(
        "app.agents.orchestrator.get_llm_provider", lambda *a, **kw: OversizedTitleLLM()
    )

    with pytest.raises(Exception) as exc_info:
        run_pipeline(postgres_session, tender, pdf_bytes)

    # The ORIGINAL database error must be what's raised — not a masking
    # PendingRollbackError/InFailedSqlTransaction from a second, unguarded
    # session operation. Positively assert the real exception type, not just
    # the absence of the specific wrong one this bug produced (that
    # negative-only assertion previously let a *different* masking
    # exception, sqlalchemy.exc.PendingRollbackError, slip through unnoticed).
    assert type(exc_info.value).__name__ == "DataError"
    assert "StringDataRightTruncation" in str(exc_info.value)

    postgres_session.commit()  # the except block's own recovery work must already be flush()-safe;
                                 # this just makes it durable, matching what the router does.

    failed = postgres_session.query(Analysis).filter(
        Analysis.tender_id == tender.id, Analysis.status == "FAILED"
    ).first()
    assert failed is not None
    assert failed.error  # the real error message was captured, not swallowed

    postgres_session.refresh(tender)
    assert tender.status == "FAILED"
