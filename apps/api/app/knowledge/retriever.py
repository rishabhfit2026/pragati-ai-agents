"""Retrieval for the RAG-powered Capability Matching Agent.

This is lexical (token-containment) retrieval, not dense/embedding retrieval —
there's no vector store wired into this demo (SQLite has no vector extension,
and standing up embeddings + pgvector is out of scope here). Classic RAG only
requires *some* retrieval step ahead of generation; ranking by keyword overlap
over a 31-product catalogue is a legitimate, cheap, fully-inspectable choice
for a knowledge base this size. Swapping in embedding-based retrieval later
only requires changing this one function — every caller just gets back a
ranked list of candidate products.
"""
from __future__ import annotations

from typing import Any


def retrieve_relevant_products(query_text: str, top_k: int = 4) -> list[dict[str, Any]]:
    from app.agents.capability_matching import overlap_score, tokenize
    from app.knowledge.loader import load_knowledge_base, searchable_product_text

    kb = load_knowledge_base()
    query_tokens = tokenize(query_text)

    scored: list[tuple[float, dict]] = []
    for product in kb["products"]:
        score, _hits = overlap_score(query_tokens, tokenize(searchable_product_text(product)))
        scored.append((score, product))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    top = [p for score, p in scored[:top_k] if score > 0]
    return top if top else [p for _, p in scored[:top_k]]
