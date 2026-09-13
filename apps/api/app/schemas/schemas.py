"""Pydantic response/request models for the API. Kept in one module deliberately —
the schema surface is large but flat; splitting it by table would add indirection
without adding clarity at this size."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TenderSummary(BaseModel):
    id: str
    title: str | None
    issuing_organization: str | None
    tender_number: str | None
    submission_deadline: str | None
    product_category: str | None
    status: str
    is_demo: bool
    uploaded_at: datetime
    final_score: float | None = None
    final_recommendation: str | None = None
    fit_label: str | None = None
    risk_label: str | None = None

    class Config:
        from_attributes = True


class TenderDetail(TenderSummary):
    filename: str
    file_hash: str
    page_count: int
    issue_date: str | None
    delivery_deadline: str | None
    geography: str | None
    estimated_quantity: str | None
    active_analysis_id: str | None

    class Config:
        from_attributes = True


class RequirementOut(BaseModel):
    id: str
    description: str
    category: str
    mandatory: bool
    confidence: float
    source_page: int | None
    source_section: str | None
    source_text_snippet: str | None

    class Config:
        from_attributes = True


class CapabilityMatchOut(BaseModel):
    id: str
    requirement_id: str
    status: str
    confidence: float
    evidence: str
    kb_reference_id: str | None
    kb_reference_name: str | None

    class Config:
        from_attributes = True


class RequirementWithMatch(RequirementOut):
    capability_match: CapabilityMatchOut | None = None


class ComplianceItemOut(BaseModel):
    id: str
    requirement_id: str | None
    title: str
    status: str
    confidence: float
    evidence: str

    class Config:
        from_attributes = True


class RiskOut(BaseModel):
    id: str
    category: str
    description: str
    severity: str
    probability: str
    evidence: str
    mitigation: str

    class Config:
        from_attributes = True


class AgentRunOut(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}

    id: str
    agent_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    retries: int
    error: str | None
    model_used: str | None
    prompt_version: str | None
    tokens_used: int | None
    output_summary: str | None


class AuditEventOut(BaseModel):
    id: str
    analysis_id: str | None
    timestamp: datetime
    event_type: str
    description: str
    actor: str
    event_metadata: dict[str, Any] | None

    class Config:
        from_attributes = True


class ScoreBreakdown(BaseModel):
    technical_fit: float | None
    capability_fit: float | None
    compliance_readiness: float | None
    strategic_fit: float | None
    commercial_attractiveness: float | None
    delivery_feasibility: float | None
    final_score: float | None
    weights: dict[str, float]
    explanation: dict[str, Any] | None


class DecisionOut(BaseModel):
    ai_recommendation: str | None
    final_recommendation: str | None
    decision_reasons: dict[str, Any] | None
    human_override: bool
    override_reason: str | None
    overridden_by: str | None
    overridden_at: datetime | None


class AnalysisOut(BaseModel):
    id: str
    tender_id: str
    created_at: datetime
    status: str
    llm_provider: str
    llm_model: str
    prompt_version: str
    scoring_version: str
    is_replay_of: str | None
    simulated_failure: str | None
    error: str | None
    score: ScoreBreakdown
    decision: DecisionOut
    requirements: list[RequirementWithMatch]
    compliance_items: list[ComplianceItemOut]
    risks: list[RiskOut]
    agent_runs: list[AgentRunOut]

    class Config:
        from_attributes = True


class DecisionOverrideRequest(BaseModel):
    final_recommendation: str = Field(pattern="^(PURSUE|REVIEW|DO_NOT_PURSUE)$")
    reason: str
    actor: str = "demo-user"


class AnalyzeRequest(BaseModel):
    simulate_failure: str | None = None  # OCR_TIMEOUT|LLM_TIMEOUT|INVALID_JSON|TOOL_ERROR


class ReplayRequest(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None
    prompt_version: str | None = None
    scoring_version: str | None = None


class ReplayComparison(BaseModel):
    old_analysis: AnalysisOut
    new_analysis: AnalysisOut
    diff: dict[str, Any]


class DashboardStats(BaseModel):
    total_opportunities: int
    high_priority: int
    review_required: int
    low_fit: int
    new_this_week: int
    average_score: float
    upcoming_deadlines: int
