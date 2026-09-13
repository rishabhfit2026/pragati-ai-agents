"""Document Intelligence Agent — section 7.

Responsible for: safe PDF parsing, OCR fallback for scanned pages, section
detection, and preserving page-level provenance for every downstream claim.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.pdf_extract import DocumentExtract, extract_document


class OCRTimeoutError(Exception):
    pass


@dataclass
class DocumentIntelligenceResult:
    document: DocumentExtract
    pages_requiring_ocr: int
    average_confidence: float


def run(file_bytes: bytes, *, simulate_failure: str | None = None) -> DocumentIntelligenceResult:
    if simulate_failure == "OCR_TIMEOUT":
        raise OCRTimeoutError("Simulated OCR timeout on scanned page batch")

    document = extract_document(file_bytes)
    ocr_pages = sum(1 for p in document.pages if p.method in ("ocr", "ocr_mock"))
    avg_conf = (
        round(sum(p.confidence for p in document.pages) / len(document.pages), 3)
        if document.pages
        else 0.0
    )
    return DocumentIntelligenceResult(document=document, pages_requiring_ocr=ocr_pages, average_confidence=avg_conf)
