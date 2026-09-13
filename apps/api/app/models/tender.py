import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=gen_id)

    # --- file / ingestion metadata ---
    filename: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[str] = mapped_column(String(1024))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- extracted tender metadata (filled by Requirement Extraction Agent) ---
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    issuing_organization: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tender_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issue_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submission_deadline: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_deadline: Mapped[str | None] = mapped_column(String(32), nullable=True)
    geography: Mapped[str | None] = mapped_column(String(128), nullable=True)
    estimated_quantity: Mapped[str | None] = mapped_column(String(128), nullable=True)
    product_category: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # --- pipeline status ---
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED")
    # UPLOADED | ANALYZING | ANALYZED | FAILED

    active_analysis_id: Mapped[str | None] = mapped_column(String(16), nullable=True)

    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="tender", cascade="all, delete-orphan", order_by="Analysis.created_at"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent", back_populates="tender", cascade="all, delete-orphan", order_by="AuditEvent.timestamp"
    )
