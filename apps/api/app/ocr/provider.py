"""OCR provider abstraction so the underlying engine can be swapped via env var
without touching document-processing code (section 26)."""
from __future__ import annotations

import io
from abc import ABC, abstractmethod

from app.config import settings


class OCRProvider(ABC):
    name: str

    @abstractmethod
    def extract_text(self, image_bytes: bytes, page_number: int) -> tuple[str, float, str]:
        """Returns (text, confidence, method_label)."""


class TesseractOCRProvider(OCRProvider):
    name = "tesseract"

    def extract_text(self, image_bytes: bytes, page_number: int) -> tuple[str, float, str]:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words = [w for w in data.get("text", []) if w.strip()]
        confs = [int(c) for c in data.get("conf", []) if c not in ("-1", -1)]
        avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.4
        return " ".join(words), round(avg_conf, 2), "ocr"


class MockOCRProvider(OCRProvider):
    """Deterministic OCR stand-in used when Tesseract is unavailable. Clearly
    labelled to the user as a simulated OCR pass so the demo never overstates
    what actually happened to the document."""

    name = "mock"

    def extract_text(self, image_bytes: bytes, page_number: int) -> tuple[str, float, str]:
        return (
            f"[Simulated OCR output for scanned page {page_number} — no OCR engine installed. "
            "In production this page would be processed by the configured OCR provider "
            "(e.g. Tesseract, cloud OCR). Content on this page could not be verified.]"
        ), 0.35, "ocr_mock"


def get_ocr_provider() -> OCRProvider:
    if settings.ocr_provider == "mock":
        return MockOCRProvider()
    if settings.ocr_provider == "tesseract":
        return TesseractOCRProvider()
    # auto: try tesseract, fall back to mock
    try:
        import pytesseract  # noqa: F401

        return TesseractOCRProvider()
    except Exception:
        return MockOCRProvider()
