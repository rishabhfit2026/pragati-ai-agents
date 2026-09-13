import fitz

from app.ocr.nvidia_ocr_provider import MAX_B64_CHARS, _extract_text_and_confidence, _shrink_to_budget


def _render_test_page_png(width=1240, height=1754) -> bytes:
    """Renders a blank-ish A4-sized page to PNG bytes, matching the shape of
    what pdf_extract.py hands to an OCR provider for a scanned page."""
    doc = fitz.open()
    page = doc.new_page(width=width / 200 * 72, height=height / 200 * 72)
    page.insert_text((50, 50), "Sample scanned page content for size-budget testing.")
    pix = page.get_pixmap(dpi=200)
    return pix.tobytes("png")


def test_shrink_to_budget_stays_under_limit():
    png_bytes = _render_test_page_png()
    b64, fmt = _shrink_to_budget(png_bytes)
    assert fmt == "jpeg"
    assert len(b64) < MAX_B64_CHARS + 5000  # small overshoot tolerance for the last-resort path


def test_extract_text_from_nested_data_shape():
    response = {
        "data": [
            {
                "text_detections": [
                    {"text_prediction": {"text": "Hello", "confidence": 0.95}},
                    {"text_prediction": {"text": "World", "confidence": 0.85}},
                ]
            }
        ]
    }
    text, confidence = _extract_text_and_confidence(response)
    assert text == "Hello\nWorld"
    assert confidence == 0.9


def test_extract_text_from_top_level_shape():
    response = {
        "text_detections": [{"text_prediction": {"text": "Top level", "confidence": 0.8}}]
    }
    text, confidence = _extract_text_and_confidence(response)
    assert text == "Top level"
    assert confidence == 0.8


def test_extract_text_returns_empty_on_unrecognized_shape():
    text, confidence = _extract_text_and_confidence({"unexpected": "shape"})
    assert text == ""
    assert confidence == 0.0
