"""Real OCR provider using NVIDIA's hosted Nemotron OCR v2 model
(https://build.nvidia.com/nvidia/nemotron-ocr-v2). Only ever instantiated
server-side, only when explicitly enabled via OCR_PROVIDER=nvidia and an
NVIDIA_OCR_API_KEY is present.

API contract (confirmed from the model's own "Shell"/"Python" code samples,
not guessed):
    POST https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2
    Authorization: Bearer <key>
    { "input": [ { "type": "image_url", "url": "data:image/<fmt>;base64,<b64>" } ] }
    - base64 payload must stay under ~180,000 chars or the (unimplemented
      here) assets API is required instead — this provider downsizes the
      rendered page image to fit rather than requiring a separate upload step.

The exact response schema isn't published on that page, so parsing here
targets the standard NVIDIA vision-NIM shape used by sibling OCR models
(data[].text_detections[].text_prediction.{text,confidence}) and logs the
raw response on first use so a mismatch is visible and fixable rather than
silently wrong.
"""
from __future__ import annotations

import base64
import logging

import fitz  # PyMuPDF
import httpx

from app.ocr.provider import OCRProvider

logger = logging.getLogger(__name__)

INVOKE_URL = "https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2"
MAX_B64_CHARS = 175_000  # NVIDIA's documented inline limit is 180,000; leave headroom


def _shrink_to_budget(image_bytes: bytes) -> tuple[str, str]:
    """Re-encodes the rendered page image as JPEG, reducing quality and then
    resolution until the base64 payload fits NVIDIA's inline-request budget.
    Returns (base64_string, image_format)."""
    pix = fitz.Pixmap(image_bytes)
    if pix.alpha:
        pix = fitz.Pixmap(pix, 0)  # drop alpha — JPEG doesn't support it

    for quality in (85, 70, 55, 40):
        data = pix.tobytes("jpg", jpg_quality=quality)
        b64 = base64.b64encode(data).decode()
        if len(b64) < MAX_B64_CHARS:
            return b64, "jpeg"

    # Still too big even at low quality — halve the resolution and retry once.
    pix.shrink(1)
    for quality in (70, 50, 35):
        data = pix.tobytes("jpg", jpg_quality=quality)
        b64 = base64.b64encode(data).decode()
        if len(b64) < MAX_B64_CHARS:
            return b64, "jpeg"

    # Last resort: return the smallest we produced, even if over budget —
    # the API call will fail with a clear error rather than hanging.
    return b64, "jpeg"


def _extract_text_and_confidence(data: dict) -> tuple[str, float]:
    detections = []
    items = data.get("data") if isinstance(data.get("data"), list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        for det in item.get("text_detections") or []:
            pred = det.get("text_prediction") if isinstance(det, dict) else None
            if isinstance(pred, dict) and pred.get("text"):
                detections.append((pred["text"], float(pred.get("confidence", 0.9))))

    if not detections:
        return "", 0.0
    text = "\n".join(t for t, _ in detections)
    avg_conf = sum(c for _, c in detections) / len(detections)
    return text, round(avg_conf, 2)


class NvidiaOCRProvider(OCRProvider):
    name = "nvidia"

    def __init__(self, api_key: str | None = None):
        from app.config import settings

        self.api_key = api_key or settings.nvidia_ocr_api_key or ""
        self._logged_once = False

    def extract_text(self, image_bytes: bytes, page_number: int) -> tuple[str, float, str]:
        b64, fmt = _shrink_to_budget(image_bytes)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {"input": [{"type": "image_url", "url": f"data:image/{fmt};base64,{b64}"}]}

        resp = httpx.post(INVOKE_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if not self._logged_once:
            logger.info("Nemotron OCR v2 raw response (page %s): %s", page_number, str(data)[:3000])
            self._logged_once = True

        text, confidence = _extract_text_and_confidence(data)
        if not text:
            logger.warning(
                "Nemotron OCR v2 returned no parseable text_detections for page %s — "
                "response shape may differ from what this provider expects: %s",
                page_number, str(data)[:1000],
            )
        return text, confidence, "ocr"
