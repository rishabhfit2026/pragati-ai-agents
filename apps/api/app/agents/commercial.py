"""Commercial / Strategic Analysis Agent.

Produces the three "business" sub-scores (strategic fit, commercial
attractiveness, delivery feasibility) that feed into the (separate,
deterministic) Scoring Engine's weighted sum. run_llm() is the active path
when a real LLM provider is configured — it grounds the model in Pragati's
public company/market facts and the tender's own metadata and asks for
scores 0-100 with justifying notes; scores are validated/clamped to [0,100]
before use. run_deterministic()/run() is the rule-based fallback used
offline and whenever the LLM's response can't be validated. Either way, the
Scoring Engine that combines these three numbers with the other three
sub-scores into a final weighted score never itself calls an LLM.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.knowledge.loader import load_knowledge_base

logger = logging.getLogger(__name__)

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


def run_deterministic(tender_metadata: dict[str, Any], requirements: list[dict[str, Any]]) -> CommercialResult:
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


COMMERCIAL_PROMPT = """You are Pragati Defence Systems' commercial/strategic analyst. Assess this tender \
opportunity against Pragati's public company profile and market position.

Respond ONLY with minified JSON with these keys:
- "strategic_fit": integer 0-100 — how well this opportunity aligns with Pragati's product lines, target
  customers, and geography
- "strategic_notes": array of 1-3 short sentences justifying that score, grounded in the company profile below
- "commercial_attractiveness": integer 0-100 — deal value/attractiveness based on quantity, repeat-order
  potential, and market size
- "commercial_notes": array of 1-3 short sentences justifying that score
- "delivery_feasibility": integer 0-100 — how workable the delivery timeline is against Pragati's disclosed
  production capacity
- "delivery_notes": array of 1-3 short sentences justifying that score

RULES:
- Ground every note in a specific fact from the company profile or tender metadata below — do not invent facts.
- Where a fact needed to judge something is not published (e.g. exact production capacity, export licenses),
  say so explicitly in the note rather than assuming it favorably.
- Be a realistic, moderately conservative analyst — a generic tender should score near 50-65, not automatically high.

TENDER METADATA:
{tender_json}

PRAGATI COMPANY PROFILE (public facts only):
{company_json}
"""


def run_llm(tender_metadata: dict[str, Any], requirements: list[dict[str, Any]], llm: Any) -> CommercialResult:
    kb = load_knowledge_base()
    company_payload = {
        "company": kb["company"],
        "manufacturing": kb["capabilities"].get("manufacturing", {}),
        "markets": kb["capabilities"].get("markets", {}),
    }
    prompt = COMMERCIAL_PROMPT.format(
        tender_json=json.dumps(tender_metadata), company_json=json.dumps(company_payload)
    )
    raw = llm.complete_json(prompt)
    if not isinstance(raw, dict):
        raise ValueError("Commercial/Strategic agent LLM response was not a JSON object")

    def _score(key: str) -> float:
        try:
            value = float(raw[key])
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Missing/invalid '{key}' in LLM response") from e
        return max(0.0, min(value, 100.0))

    def _notes(key: str) -> list[str]:
        value = raw.get(key)
        if isinstance(value, list):
            return [str(n)[:200] for n in value][:3]
        return []

    return CommercialResult(
        strategic_fit=round(_score("strategic_fit"), 1),
        strategic_notes=_notes("strategic_notes"),
        commercial_attractiveness=round(_score("commercial_attractiveness"), 1),
        commercial_notes=_notes("commercial_notes"),
        delivery_feasibility=round(_score("delivery_feasibility"), 1),
        delivery_notes=_notes("delivery_notes"),
    )


def run(tender_metadata: dict[str, Any], requirements: list[dict[str, Any]], *, llm: Any = None) -> CommercialResult:
    if llm is not None and getattr(llm, "supports_generic_completion", False):
        try:
            return run_llm(tender_metadata, requirements, llm)
        except Exception as e:
            logger.warning("LLM-based commercial/strategic analysis failed, falling back to deterministic scoring: %s", e)

    return run_deterministic(tender_metadata, requirements)
