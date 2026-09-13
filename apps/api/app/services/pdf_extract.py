"""Document Intelligence: safe PDF text extraction with per-page OCR fallback.

Design notes:
- Every extracted unit of text keeps its page number so downstream agents can
  cite a source page for every conclusion (section 7/16 of the spec).
- PyMuPDF is used directly on bytes (no shelling out, no temp-file execution of
  untrusted content) to keep PDF processing safe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF

from app.ocr.provider import get_ocr_provider

MIN_CHARS_PER_PAGE_BEFORE_OCR = 40
HEADING_RE = re.compile(r"^(?:[0-9]{1,2}[.)]\s+)?([A-Z][A-Z \-/&]{4,60})$")


@dataclass
class PageExtract:
    page_number: int  # 1-indexed
    text: str
    method: str  # "native" | "ocr" | "ocr_mock"
    confidence: float
    section: str | None = None


@dataclass
class DocumentExtract:
    pages: list[PageExtract] = field(default_factory=list)
    page_count: int = 0

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"[[PAGE {p.page_number}]]\n{p.text}" for p in self.pages)


def _guess_section(line: str) -> str | None:
    line = line.strip()
    if 4 <= len(line) <= 70 and HEADING_RE.match(line):
        return line.title()
    return None


def extract_document(file_bytes: bytes) -> DocumentExtract:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    ocr = get_ocr_provider()
    result = DocumentExtract(page_count=doc.page_count)

    current_section = "General"
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        method, confidence = "native", 0.97

        if len(text.strip()) < MIN_CHARS_PER_PAGE_BEFORE_OCR:
            # Likely a scanned page (image-only) — fall back to OCR.
            pix = page.get_pixmap(dpi=200)
            ocr_text, ocr_confidence, ocr_method = ocr.extract_text(pix.tobytes("png"), page_number=i)
            if len(ocr_text.strip()) > len(text.strip()):
                text, method, confidence = ocr_text, ocr_method, ocr_confidence

        for line in text.splitlines():
            section = _guess_section(line)
            if section:
                current_section = section
                break

        result.pages.append(
            PageExtract(page_number=i, text=text, method=method, confidence=confidence, section=current_section)
        )

    doc.close()
    return result
