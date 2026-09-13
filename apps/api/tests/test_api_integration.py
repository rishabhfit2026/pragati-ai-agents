"""End-to-end integration tests against the real FastAPI app + SQLite DB.
Exercises the same code path a real user/browser would hit."""
import io


def _make_pdf_bytes() -> bytes:
    from app.demo.tenders_data import DEMO_TENDERS
    from app.services.pdf_builder import build_tender_pdf

    entry = next(e for e in DEMO_TENDERS if e["key"] == "helmet-flagship")
    return build_tender_pdf(entry["meta"], entry["sections"])


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_rejects_non_pdf(client):
    resp = client.post("/api/tenders/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_upload_rejects_fake_pdf_extension(client):
    resp = client.post("/api/tenders/upload", files={"file": ("fake.pdf", b"not a real pdf", "application/pdf")})
    assert resp.status_code == 400


def test_full_pipeline_upload_analyze_report(client):
    pdf_bytes = _make_pdf_bytes()

    upload_resp = client.post("/api/tenders/upload", files={"file": ("tender.pdf", pdf_bytes, "application/pdf")})
    assert upload_resp.status_code == 200
    tender_id = upload_resp.json()["id"]

    analyze_resp = client.post(f"/api/tenders/{tender_id}/analyze", json={})
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()
    assert analysis["status"] == "COMPLETE"
    assert analysis["score"]["final_score"] is not None
    assert analysis["decision"]["final_recommendation"] in ("PURSUE", "REVIEW", "DO_NOT_PURSUE")
    assert len(analysis["requirements"]) > 0
    # Every requirement must carry source provenance (section 7/16).
    for req in analysis["requirements"]:
        assert req["source_page"] is not None
        assert req["source_text_snippet"]

    # Timeline should reflect the full pipeline.
    timeline = client.get(f"/api/tenders/{tender_id}/timeline").json()
    event_types = [e["event_type"] for e in timeline]
    assert "DOCUMENT_UPLOADED" in event_types
    assert "ANALYSIS_COMPLETE" in event_types

    # Report renders without error and contains the score.
    report = client.get(f"/api/tenders/{tender_id}/report.html")
    assert report.status_code == 200
    assert str(analysis["score"]["final_score"]) in report.text

    pdf_report = client.get(f"/api/tenders/{tender_id}/report.pdf")
    assert pdf_report.status_code == 200
    assert pdf_report.content.startswith(b"%PDF")


def test_human_override_is_recorded_in_audit_trail(client):
    pdf_bytes = _make_pdf_bytes()
    tender_id = client.post(
        "/api/tenders/upload", files={"file": ("tender.pdf", pdf_bytes, "application/pdf")}
    ).json()["id"]
    client.post(f"/api/tenders/{tender_id}/analyze", json={})

    override_resp = client.post(
        f"/api/tenders/{tender_id}/decision",
        json={"final_recommendation": "REVIEW", "reason": "Need to verify certification manually.", "actor": "test-user"},
    )
    assert override_resp.status_code == 200
    body = override_resp.json()
    assert body["decision"]["human_override"] is True
    assert body["decision"]["final_recommendation"] == "REVIEW"

    timeline = client.get(f"/api/tenders/{tender_id}/timeline").json()
    assert any(e["event_type"] == "HUMAN_OVERRIDE" for e in timeline)


def test_replay_produces_a_second_analysis_and_diff(client):
    pdf_bytes = _make_pdf_bytes()
    tender_id = client.post(
        "/api/tenders/upload", files={"file": ("tender.pdf", pdf_bytes, "application/pdf")}
    ).json()["id"]
    client.post(f"/api/tenders/{tender_id}/analyze", json={})

    replay_resp = client.post(f"/api/tenders/{tender_id}/replay", json={"scoring_version": "score-v2"})
    assert replay_resp.status_code == 200
    body = replay_resp.json()
    assert body["new_analysis"]["scoring_version"] == "score-v2"
    assert "score_delta" in body["diff"]

    analyses = client.get(f"/api/tenders/{tender_id}/analyses").json()
    assert len(analyses) == 2


def test_simulated_failure_recovers_via_retry_and_still_completes(client):
    pdf_bytes = _make_pdf_bytes()
    tender_id = client.post(
        "/api/tenders/upload", files={"file": ("tender.pdf", pdf_bytes, "application/pdf")}
    ).json()["id"]

    resp = client.post(f"/api/tenders/{tender_id}/analyze", json={"simulate_failure": "LLM_TIMEOUT"})
    assert resp.status_code == 200
    analysis = resp.json()
    assert analysis["status"] == "COMPLETE"
    req_agent_run = next(r for r in analysis["agent_runs"] if r["agent_name"] == "Requirement Extraction Agent")
    assert req_agent_run["status"] == "PARTIAL"
    assert req_agent_run["retries"] == 1


def test_demo_load_populates_ten_tenders_with_scores(client):
    resp = client.post("/api/demo/load")
    assert resp.status_code == 200
    assert resp.json()["count"] == 10

    tenders = client.get("/api/tenders").json()
    demo_tenders = [t for t in tenders if t["is_demo"]]
    assert len(demo_tenders) == 10
    assert all(t["final_score"] is not None for t in demo_tenders)
    recommendations = {t["final_recommendation"] for t in demo_tenders}
    # The demo set should show real variety, not everything landing in one bucket.
    assert len(recommendations) >= 2
