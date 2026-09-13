"""Executive report generation — section 23. Produces an HTML report (primary,
fully styled, printable to PDF from the browser) and a PDF report (via
reportlab) covering all required sections."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

REC_COLORS = {"PURSUE": "#16a34a", "REVIEW": "#d97706", "DO_NOT_PURSUE": "#dc2626"}


def _rec_label(rec: str | None) -> str:
    return {"PURSUE": "PURSUE", "REVIEW": "REVIEW", "DO_NOT_PURSUE": "DO NOT PURSUE"}.get(rec or "", "PENDING")


def render_html_report(tender: dict[str, Any], analysis: dict[str, Any]) -> str:
    score = analysis.get("score") or {}
    decision = analysis.get("decision") or {}
    rec = decision.get("final_recommendation")
    color = REC_COLORS.get(rec, "#64748b")
    explanation = score.get("explanation") or {}
    reasons = decision.get("decision_reasons") or {}

    def rows(items, cols):
        out = ""
        for it in items:
            out += "<tr>" + "".join(f"<td>{it.get(c, '')}</td>" for c in cols) + "</tr>"
        return out

    req_rows = rows(
        [{"description": r["description"][:140], "category": r["category"], "mandatory": "Yes" if r["mandatory"] else "No",
          "confidence": f"{r['confidence']*100:.0f}%", "page": r.get("source_page") or "-"} for r in analysis.get("requirements", [])],
        ["description", "category", "mandatory", "confidence", "page"],
    )
    comp_rows = rows(
        [{"title": c["title"], "status": c["status"], "confidence": f"{c['confidence']*100:.0f}%", "evidence": c["evidence"][:160]}
         for c in analysis.get("compliance_items", [])],
        ["title", "status", "confidence", "evidence"],
    )
    risk_rows = rows(
        [{"category": r["category"], "description": r["description"][:160], "severity": r["severity"], "probability": r["probability"], "mitigation": r["mitigation"][:160]}
         for r in analysis.get("risks", [])],
        ["category", "description", "severity", "probability", "mitigation"],
    )
    match_rows = rows(
        [{"description": r["description"][:120], "status": (r.get("capability_match") or {}).get("status", "UNKNOWN"),
          "evidence": (r.get("capability_match") or {}).get("evidence", "")[:160]} for r in analysis.get("requirements", [])],
        ["description", "status", "evidence"],
    )

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Opportunity Report — {tender.get('title') or tender.get('id')}</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;color:#0f172a;max-width:960px;margin:24px auto;padding:0 16px;}}
h1{{font-size:22px;margin-bottom:4px}} h2{{font-size:16px;margin-top:28px;border-bottom:2px solid #0f172a;padding-bottom:4px}}
.badge{{background:{color};color:#fff;padding:6px 14px;border-radius:4px;font-weight:bold;display:inline-block}}
.score{{font-size:40px;font-weight:800}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}}
td,th{{border:1px solid #cbd5e1;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#f1f5f9}}
.disclaimer{{background:#fef3c7;border:1px solid #f59e0b;padding:10px;border-radius:4px;font-size:12px;margin-top:16px}}
ul{{margin:4px 0}}
</style></head><body>
<h1>Pragati Opportunity Intelligence — Executive Report</h1>
<div class="disclaimer">PROTOTYPE — This report is generated from a publicly-sourced/synthetic Pragati capability
knowledge base and demo tender data. It is a decision-support draft, not a certified compliance or bid document.</div>

<h2>1. Executive Summary</h2>
<p><b>Tender:</b> {tender.get('title') or '—'} &nbsp; | &nbsp; <b>Customer:</b> {tender.get('issuing_organization') or '—'} &nbsp; | &nbsp; <b>Deadline:</b> {tender.get('submission_deadline') or '—'}</p>
<p class="score">{score.get('final_score') if score.get('final_score') is not None else '—'}/100</p>
<span class="badge">{_rec_label(rec)}</span>

<h2>2. Why</h2>
<ul>{''.join(f'<li>{w}</li>' for w in reasons.get('why', []))}</ul>
<h2>3. Major Concerns</h2>
<ul>{''.join(f'<li>{c}</li>' for c in reasons.get('concerns', []))}</ul>
<h2>4. Immediate Actions</h2>
<ol>{''.join(f'<li>{a}</li>' for a in reasons.get('immediate_actions', []))}</ol>

<h2>5. Tender Overview</h2>
<table><tr><th>Field</th><th>Value</th></tr>
<tr><td>Tender Number</td><td>{tender.get('tender_number') or '—'}</td></tr>
<tr><td>Issue Date</td><td>{tender.get('issue_date') or '—'}</td></tr>
<tr><td>Geography</td><td>{tender.get('geography') or '—'}</td></tr>
<tr><td>Estimated Quantity</td><td>{tender.get('estimated_quantity') or '—'}</td></tr>
<tr><td>Product Category</td><td>{tender.get('product_category') or '—'}</td></tr>
</table>

<h2>6. Key Requirements</h2>
<table><tr><th>Requirement</th><th>Category</th><th>Mandatory</th><th>Confidence</th><th>Page</th></tr>{req_rows}</table>

<h2>7. Pragati Capability Matches</h2>
<table><tr><th>Requirement</th><th>Match Status</th><th>Evidence</th></tr>{match_rows}</table>

<h2>8. Compliance Matrix</h2>
<table><tr><th>Item</th><th>Status</th><th>Confidence</th><th>Evidence</th></tr>{comp_rows}</table>

<h2>9. Risks</h2>
<table><tr><th>Category</th><th>Risk</th><th>Severity</th><th>Probability</th><th>Mitigation</th></tr>{risk_rows}</table>

<h2>10. Score Breakdown</h2>
<table><tr><th>Factor</th><th>Weight</th><th>Score</th></tr>
{''.join(f"<tr><td>{k.replace('_',' ').title()}</td><td>{int(explanation.get('weights',{}).get(k,0)*100)}%</td><td>{explanation.get('sub_scores',{}).get(k,'—')}</td></tr>" for k in ['technical_fit','capability_fit','compliance_readiness','strategic_fit','commercial_attractiveness','delivery_feasibility'])}
</table>

<h2>11. Audit Information</h2>
<p>Analysis ID: {analysis.get('id')} &nbsp;|&nbsp; Generated: {datetime.utcnow().isoformat(timespec='seconds')}Z &nbsp;|&nbsp;
Model: {analysis.get('llm_provider')}/{analysis.get('llm_model')} &nbsp;|&nbsp; Prompt version: {analysis.get('prompt_version')} &nbsp;|&nbsp; Scoring version: {analysis.get('scoring_version')}</p>

</body></html>"""


def render_pdf_report(tender: dict[str, Any], analysis: dict[str, Any]) -> bytes:
    score = analysis.get("score") or {}
    decision = analysis.get("decision") or {}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceBefore=12)
    body = styles["BodyText"]
    story = []

    story.append(Paragraph("Pragati Opportunity Intelligence — Executive Report", h1))
    story.append(Paragraph(
        "PROTOTYPE — generated from publicly-sourced/synthetic capability data and demo tender data.", body))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Tender:</b> {tender.get('title') or '—'}", body))
    story.append(Paragraph(f"<b>Customer:</b> {tender.get('issuing_organization') or '—'}", body))
    story.append(Paragraph(f"<b>Score:</b> {score.get('final_score') if score.get('final_score') is not None else '—'}/100", body))
    story.append(Paragraph(f"<b>Recommendation:</b> {_rec_label(decision.get('final_recommendation'))}", body))

    reasons = decision.get("decision_reasons") or {}
    story.append(Paragraph("Why", h2))
    for w in reasons.get("why", []):
        story.append(Paragraph(f"- {w}", body))
    story.append(Paragraph("Major Concerns", h2))
    for c in reasons.get("concerns", []):
        story.append(Paragraph(f"- {c}", body))
    story.append(Paragraph("Immediate Actions", h2))
    for i, a in enumerate(reasons.get("immediate_actions", []), 1):
        story.append(Paragraph(f"{i}. {a}", body))

    story.append(Paragraph("Compliance Matrix", h2))
    data = [["Item", "Status", "Confidence"]] + [
        [c["title"][:40], c["status"], f"{c['confidence']*100:.0f}%"] for c in analysis.get("compliance_items", [])[:20]
    ]
    if len(data) > 1:
        t = Table(data, colWidths=[70 * mm, 30 * mm, 30 * mm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke)]))
        story.append(t)

    story.append(Paragraph("Risks", h2))
    rdata = [["Category", "Severity", "Probability", "Description"]] + [
        [r["category"], r["severity"], r["probability"], r["description"][:60]] for r in analysis.get("risks", [])[:20]
    ]
    if len(rdata) > 1:
        t2 = Table(rdata, colWidths=[25 * mm, 20 * mm, 25 * mm, 60 * mm])
        t2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke)]))
        story.append(t2)

    story.append(Paragraph("Audit Information", h2))
    story.append(Paragraph(
        f"Analysis ID: {analysis.get('id')} | Model: {analysis.get('llm_provider')}/{analysis.get('llm_model')} | "
        f"Prompt: {analysis.get('prompt_version')} | Scoring: {analysis.get('scoring_version')}", body))

    doc.build(story)
    return buf.getvalue()
