"""Search across analyzed tenders — section 22.

Implemented as transparent multi-field keyword scoring today. The schema is
deliberately shaped so a real embedding/pgvector similarity search can be
substituted later without changing the API contract (search_tenders always
returns a ranked list of tender ids with a score and matched-field hints)."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.tender import Tender


def search_tenders(db: Session, query: str, limit: int = 25) -> list[dict[str, Any]]:
    query = query.strip().lower()
    if not query:
        return []
    terms = [t for t in query.split() if t]

    tenders = db.query(Tender).options(joinedload(Tender.analyses)).all()
    results = []
    for t in tenders:
        haystacks = [
            t.title or "", t.issuing_organization or "", t.tender_number or "",
            t.product_category or "", t.geography or "",
        ]
        active = next((a for a in t.analyses if a.id == t.active_analysis_id), None)
        matched_fields = set()
        score = 0
        for term in terms:
            for field_name, value in zip(
                ["title", "customer", "tender_number", "product_category", "geography"], haystacks
            ):
                if term in value.lower():
                    score += 3
                    matched_fields.add(field_name)
            if active:
                for req in active.requirements:
                    if term in req.description.lower():
                        score += 1
                        matched_fields.add("requirements")
                for risk in active.risks:
                    if term in risk.description.lower():
                        score += 1
                        matched_fields.add("risks")
                for cm in active.capability_matches:
                    if term in (cm.evidence or "").lower() or term in (cm.kb_reference_name or "").lower():
                        score += 1
                        matched_fields.add("capability_matches")
                for ci in active.compliance_items:
                    if term in ci.title.lower() or term in ci.evidence.lower():
                        score += 1
                        matched_fields.add("compliance")
        if score > 0:
            results.append({
                "tender_id": t.id, "title": t.title, "score": score,
                "matched_fields": sorted(matched_fields),
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]
