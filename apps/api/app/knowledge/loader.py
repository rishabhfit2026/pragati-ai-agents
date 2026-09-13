"""Loads Pragati's public/synthetic knowledge base from /knowledge (repo root).
Nothing here is confidential; every entry carries a _source and a confidence,
and unverified fields are explicitly marked 'Unknown — requires verification'
so downstream agents never silently upgrade an unknown into a pass."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.config import KNOWLEDGE_DIR


@lru_cache(maxsize=1)
def load_knowledge_base() -> dict[str, Any]:
    kb: dict[str, Any] = {"company": {}, "products": [], "capabilities": {}}

    company_path = KNOWLEDGE_DIR / "company.json"
    if company_path.exists():
        kb["company"] = json.loads(company_path.read_text())

    products_dir = KNOWLEDGE_DIR / "products"
    if products_dir.exists():
        for f in sorted(products_dir.glob("*.json")):
            data = json.loads(f.read_text())
            category = data.get("category", f.stem)
            for product in data.get("products", []):
                kb["products"].append({**product, "category": category, "_source": data.get("_source")})

    capabilities_dir = KNOWLEDGE_DIR / "capabilities"
    if capabilities_dir.exists():
        for f in sorted(capabilities_dir.glob("*.json")):
            kb["capabilities"][f.stem] = json.loads(f.read_text())

    return kb


_EXCLUDED_KEYS = {"id", "confidence", "unknowns", "_source", "flagship"}


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(v) for v in value)
    return str(value)


def searchable_product_text(product: dict[str, Any]) -> str:
    """Flattens every field of a knowledge-base product entry into one search
    blob. Deliberately comprehensive — weight, shelf life, coverage area,
    variants, use-cases etc. are all real evidence for capability matching,
    not just the handful of 'headline' fields."""
    parts = [_flatten(v) for k, v in product.items() if k not in _EXCLUDED_KEYS]
    return " ".join(parts).lower()
