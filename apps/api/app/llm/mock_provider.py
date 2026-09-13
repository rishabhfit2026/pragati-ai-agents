"""Deterministic, offline extraction engine used as the default LLM provider.

This is NOT a toy stub — it is a real rule-based NLP pass (regex + keyword
scoring) tuned to how Indian defence/government tender documents are typically
structured (labelled cover-sheet fields, numbered clauses, "shall/must" language
for mandatory requirements). It exists so the entire pipeline is reproducible,
free, and runnable with zero API keys, and so replay-with-a-different-provider
has a stable baseline to diff against.
"""
from __future__ import annotations

import re
from typing import Any

from app.llm.provider import LLMProvider
from app.services.pdf_extract import PageExtract

METADATA_PATTERNS: dict[str, list[re.Pattern]] = {
    "title": [re.compile(r"(?:tender|rfp|rfq)\s*(?:title|for)\s*[:\-]\s*(.+)", re.I)],
    "issuing_organization": [
        re.compile(r"(?:issuing\s*organi[sz]ation|issued\s*by|department|purchaser|buyer)\s*[:\-]\s*(.+)", re.I)
    ],
    "tender_number": [re.compile(r"(?:tender|rfp|rfq)\s*(?:no\.?|number|ref\.?)\s*[:\-]\s*(.+)", re.I)],
    "issue_date": [re.compile(r"(?:issue\s*date|date\s*of\s*issue|published\s*on)\s*[:\-]\s*(.+)", re.I)],
    "submission_deadline": [
        re.compile(r"(?:submission\s*deadline|last\s*date\s*(?:for\s*)?submission|bid\s*due\s*date|closing\s*date)\s*[:\-]\s*(.+)", re.I)
    ],
    "delivery_deadline": [
        re.compile(r"(?:delivery\s*(?:period|deadline|schedule)|supply\s*within)\s*[:\-]\s*(.+)", re.I)
    ],
    "geography": [re.compile(r"(?:place\s*of\s*delivery|delivery\s*location|geography|region)\s*[:\-]\s*(.+)", re.I)],
    "estimated_quantity": [re.compile(r"(?:estimated\s*quantity|quantity\s*required|qty\.?)\s*[:\-]\s*(.+)", re.I)],
    "product_category": [re.compile(r"(?:product\s*category|category\s*of\s*(?:supply|item)|item\s*category)\s*[:\-]\s*(.+)", re.I)],
}

# Order matters: this is a PRIORITY list, not just a scoring table. A clause
# asking the bidder to "submit valid NIJ 0101.06 certification" is
# fundamentally a certification/compliance ask even though it also names a
# ballistic standard — so administrative/compliance categories are checked
# ahead of domain/engineering categories, and the first category with a
# keyword hit wins (see _categorize below).
CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("certification", ["certificat", "iso 9001", "accredit", "nabl", "conformity"]),
    ("testing", ["test report", "tested at", "shall be tested", "type test", "ballistic test", "third-party test", "independent lab"]),
    ("eligibility", ["eligibility", "msme", "turnover of", "experience of", "years.*experience", "oem certificate", "blacklist", "export licen", "oem with"]),
    ("financial", ["emd", "earnest money", "bid security", "payment terms", "price bid", "performance bank guarantee", "pbg"]),
    ("documentation", ["documents to be submitted", "technical datasheet", "undertaking", "affidavit"]),
    ("delivery", ["delivery period", "shall be delivered", "supply within", "consignee", "dispatch", "delivered within"]),
    ("manufacturing", ["manufacturing facility", "production capacity", "manufacturing capacity", "in-house manufacturing", "production line"]),
    ("ballistic", ["ballistic", "nij ", "v50", "stanag", "back-face deformation", "bfd", "bis l", "vpam", "multi-hit", "api bz", "7.62", "5.56", "9mm", "9 mm"]),
    ("material", ["aramid", "ceramic", "uhmwpe", "dyneema", "kevlar", "composite material", "material used", "areal density"]),
    ("dimensional", ["dimension", "size of", "weight shall not exceed", "shall weigh", "mm x", "cm x", "coverage area"]),
    ("performance", ["shall defeat", "shall withstand", "shall provide protection", "back-face", "multi-hit", "shelf life"]),
]

MANDATORY_MARKERS = ["shall", "must", "mandatory", "required to", "compulsory"]
OPTIONAL_MARKERS = ["should", "preferred", "desirable", "may", "optional"]

BULLET_RE = re.compile(r"^\s*(?:[-•*]|\(?[a-zA-Z0-9]{1,3}[.)])\s+(.{15,400})$")
COVER_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z /]{2,40}:\s+\S")
SENTENCE_MIN_LEN = 35


def _categorize(line: str) -> tuple[str, float]:
    """Every bulleted/numbered clause that reaches this function IS a
    requirement (that filtering already happened at the call site) — this
    only decides which of the 12 categories it belongs to. A clause whose
    vocabulary doesn't match any specific category (e.g. software/sensor/
    integration language) still counts, filed under the general 'technical'
    bucket, rather than being silently discarded."""
    lower = line.lower()
    best_cat, best_hits = None, 0
    for cat, keywords in CATEGORY_KEYWORDS:
        hits = sum(1 for kw in keywords if re.search(kw, lower))
        if hits > 0:
            best_cat, best_hits = cat, hits
            break  # priority order — first category with any hit wins
    if best_cat is None:
        return "technical", 0.55
    confidence = min(0.6 + 0.12 * best_hits, 0.96)
    return best_cat, confidence


def _is_mandatory(line: str) -> bool:
    lower = line.lower()
    if any(m in lower for m in MANDATORY_MARKERS):
        return True
    if any(m in lower for m in OPTIONAL_MARKERS):
        return False
    return True  # conservative default: treat unmarked clauses as mandatory


def _merge_wrapped_lines(text: str) -> list[str]:
    """PDF text extraction yields one physical line per wrapped visual line,
    not per logical sentence — a long bulleted clause that wraps onto a
    second line loses its '- ' marker on the continuation. This rejoins a
    continuation line onto the previous one so a wrapped clause is treated as
    a single requirement instead of being truncated or dropped."""
    merged: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        is_new_unit = bool(BULLET_RE.match(stripped)) or bool(COVER_FIELD_RE.match(stripped)) or (
            stripped.isupper() and len(stripped) <= 70
        )
        if merged and not is_new_unit and not merged[-1].rstrip().endswith((".", ":", ";")):
            merged[-1] = merged[-1].rstrip() + " " + stripped
        else:
            merged.append(stripped)
    return merged


class MockLLMProvider(LLMProvider):
    name = "mock"

    def __init__(self, model: str = "mock-analyst-v1"):
        self.model = model

    def extract_tender_metadata(self, pages: list[PageExtract]) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        text = "\n".join(p.text for p in pages[:6])  # cover sheet is almost always in the first pages
        for field, patterns in METADATA_PATTERNS.items():
            for pattern in patterns:
                m = pattern.search(text)
                if m:
                    meta[field] = m.group(1).strip().splitlines()[0][:200]
                    break
        if "title" not in meta and pages:
            # Most tenders lead with the document title as the very first line
            # of the cover page — prefer that over scanning for ALL-CAPS text,
            # which can otherwise pick up a later section heading instead.
            first_page_lines = [l.strip() for l in pages[0].text.splitlines() if l.strip()]
            if first_page_lines:
                first_line = first_page_lines[0]
                if not COVER_FIELD_RE.match(first_line) and len(first_line) > 12:
                    meta["title"] = first_line[:200]
            if "title" not in meta:
                candidates = [l for l in first_page_lines if len(l) > 12 and l.isupper()]
                if candidates:
                    meta["title"] = candidates[0].title()
        return meta

    def extract_requirements(self, pages: list[PageExtract]) -> list[dict[str, Any]]:
        requirements: list[dict[str, Any]] = []
        seen: set[str] = set()

        for page in pages:
            per_page_count = 0
            for raw_line in _merge_wrapped_lines(page.text):
                if per_page_count >= 20:
                    break
                line = raw_line.strip()
                if len(line) < 15:
                    continue
                if COVER_FIELD_RE.match(line):
                    continue  # cover-sheet metadata line ("Label: value"), not a requirement

                # Only bulleted/numbered clauses are treated as requirements —
                # this deliberately excludes titles, section headings, and
                # narrative paragraphs, which are not discrete requirements.
                bullet_match = BULLET_RE.match(line)
                if not bullet_match:
                    continue
                candidate = bullet_match.group(1).strip()

                if len(candidate) < SENTENCE_MIN_LEN:
                    continue

                cat_result = _categorize(candidate)
                if not cat_result:
                    continue
                category, confidence = cat_result

                key = candidate.lower()[:80]
                if key in seen:
                    continue
                seen.add(key)

                requirements.append(
                    {
                        "description": candidate[:500],
                        "category": category,
                        "mandatory": _is_mandatory(candidate),
                        "confidence": round(confidence * page.confidence, 2),
                        "source_page": page.page_number,
                        "source_section": page.section,
                        "source_text_snippet": candidate[:300],
                    }
                )
                per_page_count += 1

        return requirements
