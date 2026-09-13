from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.search import search_tenders

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(q: str, db: Session = Depends(get_db)):
    return {"query": q, "results": search_tenders(db, q)}
