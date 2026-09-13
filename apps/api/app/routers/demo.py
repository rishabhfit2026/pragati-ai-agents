from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.demo.generator import load_demo_data, clear_demo_data

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/load")
def load_demo(db: Session = Depends(get_db)):
    return load_demo_data(db)


@router.post("/clear")
def clear_demo(db: Session = Depends(get_db)):
    clear_demo_data(db)
    return {"status": "cleared"}
