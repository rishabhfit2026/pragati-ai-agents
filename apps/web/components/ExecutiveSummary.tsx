"use client";

import { useState } from "react";
import type { AnalysisOut, Recommendation, TenderDetail } from "@/lib/types";
import { RecBadge, ScoreDial, Button } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

const OPTIONS: { value: Recommendation; label: string }[] = [
  { value: "PURSUE", label: "Pursue" },
  { value: "REVIEW", label: "Review" },
  { value: "DO_NOT_PURSUE", label: "Do Not Pursue" },
];

export default function ExecutiveSummary({
  tender,
  analysis,
  onOverride,
}: {
  tender: TenderDetail;
  analysis: AnalysisOut;
  onOverride: (a: AnalysisOut) => void;
}) {
  const [overriding, setOverriding] = useState(false);
  const [reason, setReason] = useState("");
  const [choice, setChoice] = useState(analysis.decision.final_recommendation || "REVIEW");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reasons = analysis.decision.decision_reasons;

  async function submitOverride() {
    if (!reason.trim()) {
      setError("Please provide a reason for the override — it is recorded in the audit trail.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const updated = await api.overrideDecision(tender.id, choice, reason, "demo-user");
      onOverride(updated);
      setOverriding(false);
      setReason("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Override failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <ScoreDial score={analysis.score.final_score} size={110} />
        <div style={{ flex: 1, minWidth: 260 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <h1 style={{ fontSize: 19, fontWeight: 800 }}>{tender.title || "(untitled tender)"}</h1>
            {tender.is_demo && (
              <span className="badge" style={{ background: "rgba(148,163,184,0.15)", color: "#94a3b8" }}>DEMO DATA</span>
            )}
          </div>
          <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4 }}>
            {tender.issuing_organization} &nbsp;•&nbsp; {tender.tender_number} &nbsp;•&nbsp; Deadline:{" "}
            {tender.submission_deadline || "—"}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
            <RecBadge rec={analysis.decision.final_recommendation} />
            {analysis.decision.human_override && (
              <span style={{ fontSize: 11.5, color: "var(--muted)" }}>
                (human override — AI recommended <b>{analysis.decision.ai_recommendation}</b>)
              </span>
            )}
            <Button variant="ghost" onClick={() => setOverriding((v) => !v)}>
              {overriding ? "Cancel" : "Human Review / Override"}
            </Button>
          </div>

          {overriding && (
            <div className="card-2" style={{ padding: 14, marginTop: 12 }}>
              <div style={{ display: "flex", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
                {OPTIONS.map((o) => (
                  <label key={o.value} style={{ fontSize: 12.5, display: "flex", alignItems: "center", gap: 5 }}>
                    <input
                      type="radio"
                      checked={choice === o.value}
                      onChange={() => setChoice(o.value)}
                      name="override-choice"
                    />
                    {o.label}
                  </label>
                ))}
              </div>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Reason for this decision (required, recorded in the audit trail)…"
                rows={2}
                style={{
                  width: "100%",
                  background: "var(--panel)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: 8,
                  fontSize: 12.5,
                  color: "var(--text)",
                  resize: "vertical",
                }}
              />
              {error && <div style={{ color: "#f87171", fontSize: 12, marginTop: 6 }}>{error}</div>}
              <div style={{ marginTop: 8 }}>
                <Button onClick={submitOverride} disabled={submitting}>
                  Submit Override
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginTop: 20, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
        <div>
          <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700, marginBottom: 6 }}>WHY</div>
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12.5, display: "flex", flexDirection: "column", gap: 4 }}>
            {(reasons?.why || []).map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
        <div>
          <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700, marginBottom: 6 }}>MAJOR CONCERNS</div>
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12.5, display: "flex", flexDirection: "column", gap: 4 }}>
            {(reasons?.concerns || []).map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
        <div>
          <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700, marginBottom: 6 }}>IMMEDIATE ACTIONS</div>
          <ol style={{ margin: 0, paddingLeft: 16, fontSize: 12.5, display: "flex", flexDirection: "column", gap: 4 }}>
            {(reasons?.immediate_actions || []).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
