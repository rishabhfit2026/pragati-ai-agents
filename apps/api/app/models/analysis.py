from datetime import datetime

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.tender import gen_id


class Analysis(Base):
    """One run of the full agent pipeline against a tender. A tender can have
    multiple analyses over time (re-analysis, replay-with-different-config)."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)
    tender_id: Mapped[str] = mapped_column(ForeignKey("tenders.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")  # RUNNING | COMPLETE | FAILED

    # --- run configuration (for replay / observability / auditability) ---
    llm_provider: Mapped[str] = mapped_column(String(64), default="mock")
    llm_model: Mapped[str] = mapped_column(String(64), default="mock-analyst-v1")
    prompt_version: Mapped[str] = mapped_column(String(32), default="req-extract-v1")
    scoring_version: Mapped[str] = mapped_column(String(32), default="score-v1")
    is_replay_of: Mapped[str | None] = mapped_column(String(16), nullable=True)
    simulated_failure: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- scoring (structured, deterministic — never a raw LLM number) ---
    technical_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    capability_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_readiness: Mapped[float | None] = mapped_column(Float, nullable=True)
    strategic_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    commercial_attractiveness: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_feasibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- decision ---
    ai_recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)  # PURSUE|REVIEW|DO_NOT_PURSUE
    final_recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision_reasons: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    human_override: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    tender: Mapped["Tender"] = relationship("Tender", back_populates="analyses")
    requirements: Mapped[list["Requirement"]] = relationship(
        "Requirement", back_populates="analysis", cascade="all, delete-orphan"
    )
    capability_matches: Mapped[list["CapabilityMatch"]] = relationship(
        "CapabilityMatch", back_populates="analysis", cascade="all, delete-orphan"
    )
    compliance_items: Mapped[list["ComplianceItem"]] = relationship(
        "ComplianceItem", back_populates="analysis", cascade="all, delete-orphan"
    )
    risks: Mapped[list["Risk"]] = relationship(
        "Risk", back_populates="analysis", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="analysis", cascade="all, delete-orphan", order_by="AgentRun.started_at"
    )


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)

    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64))
    # technical|ballistic|material|dimensional|performance|certification|testing|
    # manufacturing|documentation|delivery|financial|eligibility
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_section: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_text_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="requirements")
    capability_match: Mapped["CapabilityMatch"] = relationship(
        "CapabilityMatch", back_populates="requirement", uselist=False
    )


class CapabilityMatch(Base):
    __tablename__ = "capability_matches"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"), index=True)

    status: Mapped[str] = mapped_column(String(16))  # MATCH|PARTIAL_MATCH|UNKNOWN|GAP
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence: Mapped[str] = mapped_column(Text)
    kb_reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kb_reference_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="capability_matches")
    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="capability_match")


class ComplianceItem(Base):
    __tablename__ = "compliance_items"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    requirement_id: Mapped[str | None] = mapped_column(ForeignKey("requirements.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16))  # MATCH|UNKNOWN|GAP
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence: Mapped[str] = mapped_column(Text)

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="compliance_items")


class Risk(Base):
    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)

    category: Mapped[str] = mapped_column(String(32))
    # TECHNICAL|COMPLIANCE|COMMERCIAL|OPERATIONAL|DELIVERY|DOCUMENTATION|COMPETITION
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16))  # LOW|MEDIUM|HIGH
    probability: Mapped[str] = mapped_column(String(16))  # LOW|MEDIUM|HIGH
    evidence: Mapped[str] = mapped_column(Text)
    mitigation: Mapped[str] = mapped_column(Text)

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="risks")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)

    agent_name: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="RUNNING")  # RUNNING|SUCCESS|PARTIAL|FAILED
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="agent_runs")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)
    tender_id: Mapped[str] = mapped_column(ForeignKey("tenders.id"), index=True)
    analysis_id: Mapped[str | None] = mapped_column(String(16), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    event_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(128), default="system")
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    tender: Mapped["Tender"] = relationship("Tender", back_populates="audit_events")
