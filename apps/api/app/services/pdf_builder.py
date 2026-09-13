"""Builds realistic synthetic tender PDFs for demo data (section 29) using
reportlab. Cover-sheet fields use 'Label: value' lines and body clauses use
'- ' bullets so the mock extraction engine (tuned to this exact shape, as most
real Indian government/defence tenders are also formatted) can parse them."""
from __future__ import annotations

import io
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak


def build_tender_pdf(meta: dict[str, Any], sections: list[dict[str, Any]]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=16)
    label_style = ParagraphStyle("label", parent=styles["Normal"], fontSize=11, spaceAfter=6)
    heading_style = ParagraphStyle("heading", parent=styles["Heading2"], fontSize=13, spaceBefore=14)
    bullet_style = ParagraphStyle("bullet", parent=styles["Normal"], fontSize=10.5, spaceAfter=6, leftIndent=10)

    story = [
        Paragraph(meta.get("title", "Tender Document"), title_style),
        Spacer(1, 10),
        Paragraph(f"Tender Number: {meta.get('tender_number', '')}", label_style),
        Paragraph(f"Issuing Organization: {meta.get('issuing_organization', '')}", label_style),
        Paragraph(f"Issue Date: {meta.get('issue_date', '')}", label_style),
        Paragraph(f"Submission Deadline: {meta.get('submission_deadline', '')}", label_style),
        Paragraph(f"Delivery Deadline: {meta.get('delivery_deadline', '')}", label_style),
        Paragraph(f"Geography: {meta.get('geography', '')}", label_style),
        Paragraph(f"Estimated Quantity: {meta.get('estimated_quantity', '')}", label_style),
        Paragraph(f"Product Category: {meta.get('product_category', '')}", label_style),
        PageBreak(),
    ]

    for section in sections:
        story.append(Paragraph(section["heading"], heading_style))
        for item in section["items"]:
            story.append(Paragraph(f"- {item}", bullet_style))

    doc.build(story)
    return buf.getvalue()
