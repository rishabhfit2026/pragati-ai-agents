from __future__ import annotations

from typing import Any

from app.agents.scoring import WEIGHTS, WEIGHTS_BY_VERSION
from app.models.analysis import Analysis
from app.models.tender import Tender


def tender_to_dict(t: Tender) -> dict[str, Any]:
    return {
        "id": t.id, "title": t.title, "issuing_organization": t.issuing_organization,
        "tender_number": t.tender_number, "issue_date": t.issue_date,
        "submission_deadline": t.submission_deadline, "delivery_deadline": t.delivery_deadline,
        "geography": t.geography, "estimated_quantity": t.estimated_quantity,
        "product_category": t.product_category, "status": t.status, "is_demo": t.is_demo,
        "filename": t.filename, "file_hash": t.file_hash, "page_count": t.page_count,
    }


def analysis_to_dict(a: Analysis) -> dict[str, Any]:
    requirements = []
    for r in a.requirements:
        cm = r.capability_match
        requirements.append({
            "id": r.id, "description": r.description, "category": r.category, "mandatory": r.mandatory,
            "confidence": r.confidence, "source_page": r.source_page, "source_section": r.source_section,
            "source_text_snippet": r.source_text_snippet,
            "capability_match": None if not cm else {
                "id": cm.id, "requirement_id": cm.requirement_id, "status": cm.status, "confidence": cm.confidence,
                "evidence": cm.evidence, "kb_reference_id": cm.kb_reference_id, "kb_reference_name": cm.kb_reference_name,
            },
        })
    compliance_items = [{
        "id": c.id, "requirement_id": c.requirement_id, "title": c.title, "status": c.status,
        "confidence": c.confidence, "evidence": c.evidence,
    } for c in a.compliance_items]
    risks = [{
        "id": r.id, "category": r.category, "description": r.description, "severity": r.severity,
        "probability": r.probability, "evidence": r.evidence, "mitigation": r.mitigation,
    } for r in a.risks]
    agent_runs = [{
        "id": ar.id, "agent_name": ar.agent_name, "status": ar.status, "started_at": ar.started_at,
        "finished_at": ar.finished_at, "duration_ms": ar.duration_ms, "retries": ar.retries, "error": ar.error,
        "model_used": ar.model_used, "prompt_version": ar.prompt_version, "tokens_used": ar.tokens_used,
        "output_summary": ar.output_summary,
    } for ar in a.agent_runs]

    return {
        "id": a.id, "tender_id": a.tender_id, "created_at": a.created_at, "status": a.status,
        "llm_provider": a.llm_provider, "llm_model": a.llm_model, "prompt_version": a.prompt_version,
        "scoring_version": a.scoring_version, "is_replay_of": a.is_replay_of, "simulated_failure": a.simulated_failure,
        "error": a.error,
        "score": {
            "technical_fit": a.technical_fit, "capability_fit": a.capability_fit,
            "compliance_readiness": a.compliance_readiness, "strategic_fit": a.strategic_fit,
            "commercial_attractiveness": a.commercial_attractiveness, "delivery_feasibility": a.delivery_feasibility,
            "final_score": a.final_score,
            "weights": WEIGHTS_BY_VERSION.get(a.scoring_version, WEIGHTS),
            "explanation": a.score_explanation,
        },
        "decision": {
            "ai_recommendation": a.ai_recommendation, "final_recommendation": a.final_recommendation,
            "decision_reasons": a.decision_reasons, "human_override": a.human_override,
            "override_reason": a.override_reason, "overridden_by": a.overridden_by, "overridden_at": a.overridden_at,
        },
        "requirements": requirements,
        "compliance_items": compliance_items,
        "risks": risks,
        "agent_runs": agent_runs,
    }


def fit_label(score: float | None) -> str:
    if score is None:
        return "—"
    if score >= 75:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"


def risk_label(analysis: Analysis | None) -> str:
    if not analysis or not analysis.risks:
        return "—"
    high = sum(1 for r in analysis.risks if r.severity == "HIGH")
    if high >= 2:
        return "High"
    if high == 1 or len(analysis.risks) >= 3:
        return "Medium"
    return "Low"
