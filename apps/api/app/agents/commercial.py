"""Commercial / Strategic Analysis Agent.

Computes the three "business" sub-scores (strategic fit, commercial
attractiveness, delivery feasibility) from structured signals — never from a
free-form LLM number — so every point can be traced to a rule.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.knowledge.loader import load_knowledge_base

QUANTITY_RE = re.compile(r"([\d,]{2,})")
SHORT_WINDOW_RE = re.compile(r"\b(\d{1,3})\s*(day|days)\b", re.I)
LONG_WINDOW_RE = re.compile(r"\b(\d{1,2})\s*(month|months|year|years)\b", re.I)

DEFENCE_ORG_KEYWORDS = [
    "army", "navy", "naval", "air force", "defence", "defense", "ministry of defence", "mod",
    "police", "paramilitary", "coast guard", "crpf", "bsf", "border security", "drdo",
    "special forces", "armed police", "security force", "rapid action force",
]
PRAGATI_CATEGORY_KEYWORDS = ["helmet", "vest", "carrier", "armour", "armor", "plate", "shield", "vehicle protection", "ballistic", "body armour", "body armor"]


@dataclass
class CommercialResult:
    strategic_fit: float
    strategic_notes: list[str]
    commercial_attractiveness: float
    commercial_notes: list[str]
    delivery_feasibility: float
    delivery_notes: list[str]


def score_strategic_fit(tender_metadata: dict[str, Any]) -> tuple[float, list[str]]:
    score, notes = 55.0, []
    category = str(tender_metadata.get("product_category") or "").lower()
    org = str(tender_metadata.get("issuing_organization") or "").lower()
    geography = str(tender_metadata.get("geography") or "").lower()

    if any(k in category for k in PRAGATI_CATEGORY_KEYWORDS):
        score += 25
        notes.append("Product category directly matches Pragati's published product lines.")
    else:
        notes.append("Product category could not be confidently matched to a Pragati product line.")

    if any(k in org for k in DEFENCE_ORG_KEYWORDS):
        score += 15
        notes.append("Issuing organization is a defence/paramilitary body — Pragati's core target market.")

    if "india" in geography or not geography:
        score += 5
        notes.append("Geography is within Pragati's primary (Indian) market.")
    else:
        notes.append("Geography is outside Pragati's publicly confirmed primary market — export readiness unverified.")

    return round(min(score, 100.0), 1), notes


def score_commercial_attractiveness(tender_metadata: dict[str, Any]) -> tuple[float, list[str]]:
    score, notes = 55.0, []
    qty_text = str(tender_metadata.get("estimated_quantity") or "").replace(",", "")
    m = QUANTITY_RE.search(qty_text)
    if m:
        qty = int(m.group(1))
        if qty >= 5000:
            score += 25
            notes.append(f"Large estimated quantity ({qty:,} units) makes this a high commercial-value opportunity.")
        elif qty >= 500:
            score += 12
            notes.append(f"Moderate estimated quantity ({qty:,} units).")
        else:
            notes.append(f"Estimated quantity ({qty:,} units) is relatively small.")
    else:
        notes.append("Estimated quantity not clearly specified in the tender — commercial value uncertain.")

    return round(min(score, 100.0), 1), notes


def score_delivery_feasibility(tender_metadata: dict[str, Any], requirements: list[dict[str, Any]]) -> tuple[float, list[str]]:
    score, notes = 70.0, []
    kb = load_knowledge_base()
    text = str(tender_metadata.get("delivery_deadline") or "")
    text += " " + " ".join(r["description"] for r in requirements if r["category"] == "delivery")

    short = SHORT_WINDOW_RE.search(text)
    long_ = LONG_WINDOW_RE.search(text)
    if short and int(short.group(1)) <= 45:
        score -= 25
        notes.append(f"Tight delivery window detected ('{short.group(0)}') relative to typical manufacturing lead times.")
    elif long_:
        score += 15
        notes.append(f"Delivery window ('{long_.group(0)}') appears workable against a standard production schedule.")
    else:
        notes.append("Delivery timeline not clearly specified — feasibility could not be fully assessed.")

    capacity = kb["capabilities"].get("manufacturing", {}).get("stated_capacity", {}).get("spall_liner")
    if capacity:
        notes.append(f"Pragati publicly states {capacity} of relevant production throughput.")

    return round(max(min(score, 100.0), 0.0), 1), notes


def run(tender_metadata: dict[str, Any], requirements: list[dict[str, Any]]) -> CommercialResult:
    strategic, strategic_notes = score_strategic_fit(tender_metadata)
    commercial, commercial_notes = score_commercial_attractiveness(tender_metadata)
    delivery, delivery_notes = score_delivery_feasibility(tender_metadata, requirements)
    return CommercialResult(
        strategic_fit=strategic,
        strategic_notes=strategic_notes,
        commercial_attractiveness=commercial,
        commercial_notes=commercial_notes,
        delivery_feasibility=delivery,
        delivery_notes=delivery_notes,
    )
