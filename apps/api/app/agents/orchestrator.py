"""Agent orchestrator — the workflow graph described in section 6:

Tender -> Document Intelligence -> Requirement Extraction -> Eligibility &
Compliance -> Capability Matching -> Risk Analysis -> Commercial/Strategic
Analysis -> Opportunity Scoring -> Decision -> Human Review

Each stage is timed and logged as an AgentRun row, with a simple
retry -> fallback -> success pattern for the developer-mode failure simulator
(section 21). This is NOT LangGraph itself (to avoid a hard dependency on an
external package/API being reachable in this environment) but it implements
the same explicit-node/explicit-edge state-machine shape, which is what
actually matters for reliability and observability.
"""
from __future__ import annotations

import time
import traceback
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agents import capability_matching, commercial, compliance, decision, document_intelligence, risk, scoring
from app.agents.requirement_extraction import run as extract_requirements
from app.agents.errors import ToolError
from app.llm.provider import LLMTimeoutError, InvalidJSONError, get_llm_provider
from app.models.analysis import (
    Analysis, Requirement, CapabilityMatch, ComplianceItem, Risk, AgentRun,
)
from app.models.tender import Tender
from app.services.audit import log_event

MAX_RETRIES = 1


def _run_stage(
    db: Session,
    analysis_id: str,
    agent_name: str,
    fn: Callable[[bool], Any],
    *,
    model_used: str | None = None,
    prompt_version: str | None = None,
) -> tuple[Any, AgentRun]:
    """Runs `fn(is_retry)` with up to MAX_RETRIES retries. On the first
    failure, retries once with the failure condition cleared (simulating a
    fallback path: smaller/mocked model, cached KB copy, etc.) This is the
    Failure -> Retry -> Fallback -> Success loop from section 21."""
    started = datetime.utcnow()
    t0 = time.perf_counter()
    retries = 0
    error_note = None
    result = None
    status = "SUCCESS"

    for attempt in range(MAX_RETRIES + 1):
        try:
            result = fn(attempt > 0)
            break
        except (LLMTimeoutError, InvalidJSONError, ToolError, document_intelligence.OCRTimeoutError, ValueError) as e:
            error_note = f"{type(e).__name__}: {e}"
            retries = attempt + 1
            if attempt >= MAX_RETRIES:
                status = "FAILED"
            continue
        except Exception as e:
            error_note = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=2)}"
            status = "FAILED"
            break

    duration_ms = int((time.perf_counter() - t0) * 1000)
    if status != "FAILED" and retries > 0:
        status = "PARTIAL"

    run_row = AgentRun(
        analysis_id=analysis_id,
        agent_name=agent_name,
        status=status,
        started_at=started,
        finished_at=datetime.utcnow(),
        duration_ms=duration_ms,
        retries=retries,
        error=error_note,
        model_used=model_used,
        prompt_version=prompt_version,
        output_summary=(
            f"Recovered via fallback after {retries} retry(ies)." if status == "PARTIAL"
            else ("Failed after retries." if status == "FAILED" else None)
        ),
    )
    db.add(run_row)
    db.flush()

    if status == "FAILED":
        raise RuntimeError(f"{agent_name} failed: {error_note}")

    return result, run_row


def run_pipeline(
    db: Session,
    tender: Tender,
    file_bytes: bytes,
    *,
    llm_provider_name: str | None = None,
    llm_model: str | None = None,
    prompt_version: str | None = None,
    scoring_version: str | None = None,
    simulate_failure: str | None = None,
    is_replay_of: str | None = None,
) -> Analysis:
    from app.config import settings

    llm = get_llm_provider(llm_provider_name, llm_model)
    prompt_version = prompt_version or settings.prompt_version
    scoring_version = scoring_version or settings.scoring_version

    def sim(name: str) -> str | None:
        """Only inject the simulated failure into the stage it targets."""
        return simulate_failure if simulate_failure == name else None

    analysis = Analysis(
        tender_id=tender.id,
        status="RUNNING",
        llm_provider=llm.name,
        llm_model=llm.model,
        prompt_version=prompt_version,
        scoring_version=scoring_version,
        is_replay_of=is_replay_of,
        simulated_failure=simulate_failure,
    )
    db.add(analysis)
    db.flush()

    log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="ANALYSIS_STARTED",
              description=f"Analysis started (provider={llm.name}, model={llm.model}, prompt={prompt_version}, scoring={scoring_version})")

    try:
        tender.status = "ANALYZING"
        db.flush()

        # 1. Document Intelligence
        di_result, _ = _run_stage(
            db, analysis.id, "Document Intelligence Agent",
            lambda is_retry: document_intelligence.run(
                file_bytes, simulate_failure=None if is_retry else sim("OCR_TIMEOUT")
            ),
        )
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="TEXT_EXTRACTED",
                  description=f"Text extracted from {di_result.document.page_count} page(s); {di_result.pages_requiring_ocr} required OCR fallback.")

        # 2. Requirement Extraction
        req_result, req_run_row = _run_stage(
            db, analysis.id, "Requirement Extraction Agent",
            lambda is_retry: extract_requirements(
                di_result.document, llm,
                simulate_failure=None if is_retry else (sim("LLM_TIMEOUT") or sim("INVALID_JSON")),
            ),
            model_used=llm.model, prompt_version=prompt_version,
        )
        # For a failover chain, `llm.model` above is just the static list of
        # candidates — once a call has actually gone through, reflect which
        # one really served it, for accurate observability/audit records.
        actually_used = getattr(llm, "last_used", None)
        if actually_used is not None:
            req_run_row.model_used = llm.last_used_label
            analysis.llm_provider = actually_used.name
            analysis.llm_model = actually_used.model
            db.flush()
        requirements_data = req_result.requirements
        tender_metadata = req_result.metadata
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="REQUIREMENTS_EXTRACTED",
                  description=f"{len(requirements_data)} requirement(s) extracted from tender text.")

        # persist tender metadata (from latest analysis)
        for field in ("title", "issuing_organization", "tender_number", "issue_date", "submission_deadline",
                       "delivery_deadline", "geography", "estimated_quantity", "product_category"):
            value = tender_metadata.get(field)
            if value:
                setattr(tender, field, value)
        tender.page_count = di_result.document.page_count

        # persist requirements
        requirement_rows: list[Requirement] = []
        for r in requirements_data:
            row = Requirement(
                analysis_id=analysis.id,
                description=r["description"],
                category=r["category"],
                mandatory=r["mandatory"],
                confidence=r["confidence"],
                source_page=r.get("source_page"),
                source_section=r.get("source_section"),
                source_text_snippet=r.get("source_text_snippet"),
            )
            db.add(row)
            requirement_rows.append(row)
        db.flush()

        # 3. Capability Matching
        match_results, _ = _run_stage(
            db, analysis.id, "Capability Matching Agent",
            lambda is_retry: capability_matching.run(
                requirements_data,
                simulate_failure=None if is_retry else sim("TOOL_ERROR"),
            ),
        )
        for row, m in zip(requirement_rows, match_results):
            db.add(CapabilityMatch(
                analysis_id=analysis.id, requirement_id=row.id, status=m.status, confidence=m.confidence,
                evidence=m.evidence, kb_reference_id=m.kb_reference_id, kb_reference_name=m.kb_reference_name,
            ))
        db.flush()
        gap_count = sum(1 for m in match_results if m.status == "GAP")
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="CAPABILITY_MATCHED",
                  description=f"Capability matching complete — {gap_count} gap(s) identified against {len(match_results)} requirement(s).")

        # 4. Compliance
        compliance_results, _ = _run_stage(
            db, analysis.id, "Eligibility & Compliance Agent",
            lambda is_retry: compliance.run(requirements_data),
        )
        for idx, c in compliance_results:
            db.add(ComplianceItem(
                analysis_id=analysis.id, requirement_id=requirement_rows[idx].id, title=c.title,
                status=c.status, confidence=c.confidence, evidence=c.evidence,
            ))
        db.flush()
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="COMPLIANCE_ANALYZED",
                  description=f"Compliance matrix built with {len(compliance_results)} item(s).")

        # 5. Risk
        risk_results, _ = _run_stage(
            db, analysis.id, "Risk Analysis Agent",
            lambda is_retry: risk.run(
                requirements=requirements_data, capability_matches=match_results,
                compliance_results=compliance_results, tender_metadata=tender_metadata,
            ),
        )
        for rk in risk_results:
            db.add(Risk(
                analysis_id=analysis.id, category=rk.category, description=rk.description,
                severity=rk.severity, probability=rk.probability, evidence=rk.evidence, mitigation=rk.mitigation,
            ))
        db.flush()
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="RISK_ANALYZED",
                  description=f"{len(risk_results)} risk(s) identified across the risk register.")

        # 6. Commercial / Strategic
        commercial_result, _ = _run_stage(
            db, analysis.id, "Commercial & Strategic Analysis Agent",
            lambda is_retry: commercial.run(tender_metadata, requirements_data),
        )

        # 7. Scoring (deterministic)
        score_result, _ = _run_stage(
            db, analysis.id, "Opportunity Scoring Agent",
            lambda is_retry: scoring.compute_score(
                requirements=requirements_data, capability_matches=match_results,
                compliance_results=compliance_results, commercial=commercial_result,
                scoring_version=scoring_version,
            ),
        )
        analysis.technical_fit = score_result.technical_fit
        analysis.capability_fit = score_result.capability_fit
        analysis.compliance_readiness = score_result.compliance_readiness
        analysis.strategic_fit = score_result.strategic_fit
        analysis.commercial_attractiveness = score_result.commercial_attractiveness
        analysis.delivery_feasibility = score_result.delivery_feasibility
        analysis.final_score = score_result.final_score
        analysis.score_explanation = score_result.explanation
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="SCORE_CALCULATED",
                  description=f"Opportunity score calculated: {score_result.final_score}/100.")

        # 8. Decision
        decision_result, _ = _run_stage(
            db, analysis.id, "Decision Agent",
            lambda is_retry: decision.decide(
                final_score=score_result.final_score, requirements=requirements_data,
                capability_matches=match_results, compliance_results=compliance_results,
                score_explanation=score_result.explanation,
            ),
        )
        analysis.ai_recommendation = decision_result.recommendation
        analysis.final_recommendation = decision_result.recommendation
        analysis.decision_reasons = decision_result.reasons
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="RECOMMENDATION_GENERATED",
                  description=f"Recommendation generated: {decision_result.recommendation}.")

        analysis.status = "COMPLETE"
        tender.status = "ANALYZED"
        tender.active_analysis_id = analysis.id
        db.flush()
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="ANALYSIS_COMPLETE",
                  description="Analysis pipeline completed successfully.")

    except Exception as e:
        analysis.status = "FAILED"
        analysis.error = str(e)
        tender.status = "FAILED"
        db.flush()
        log_event(db, tender_id=tender.id, analysis_id=analysis.id, event_type="ANALYSIS_FAILED",
                  description=f"Analysis pipeline failed: {e}")
        raise

    return analysis
