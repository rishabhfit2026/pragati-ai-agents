from __future__ import annotations

from fastapi import APIRouter

from app.knowledge.loader import load_knowledge_base

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("")
def get_knowledge_base():
    return load_knowledge_base()
