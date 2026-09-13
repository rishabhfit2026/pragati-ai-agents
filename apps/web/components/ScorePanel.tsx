"use client";

import type { ScoreBreakdown } from "@/lib/types";
import { ScoreDial } from "@/components/ui";

const LABELS: Record<string, string> = {
  technical_fit: "Technical Fit",
  capability_fit: "Capability Fit",
  compliance_readiness: "Compliance Readiness",
  strategic_fit: "Strategic Fit",
  commercial_attractiveness: "Commercial Attractiveness",
  delivery_feasibility: "Delivery Feasibility",
};

export default function ScorePanel({ score }: { score: ScoreBreakdown }) {
  const weights = score.explanation?.weights || score.weights;
  const subs = score.explanation?.sub_scores || {};

  return (
    <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
      <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", alignItems: "center", gap: 10, minWidth: 180 }}>
        <ScoreDial score={score.final_score} size={120} />
        <div style={{ fontSize: 11, color: "var(--muted)" }}>
          Scoring version: <span className="mono">{score.explanation?.scoring_version || "score-v1"}</span>
        </div>
      </div>

      <div className="card" style={{ flex: 1, minWidth: 320, padding: 18 }}>
        <div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Weighted Factor Breakdown
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {Object.keys(LABELS).map((key) => {
            const val = subs[key] ?? 0;
            const weight = weights[key] ?? 0;
            const color = val >= 75 ? "#4ade80" : val >= 55 ? "#fbbf24" : "#f87171";
            return (
              <div key={key}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                  <span>
                    {LABELS[key]} <span style={{ color: "var(--muted)" }}>({Math.round(weight * 100)}%)</span>
                  </span>
                  <span className="mono" style={{ fontWeight: 700 }}>{val.toFixed(1)}</span>
                </div>
                <div style={{ height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ width: `${val}%`, height: "100%", background: color }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card" style={{ flex: 1, minWidth: 280, padding: 18 }}>
        <div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, marginBottom: 10, textTransform: "uppercase" }}>Why this score</div>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, display: "flex", flexDirection: "column", gap: 6 }}>
          {(score.explanation?.strengths || []).map((s, i) => (
            <li key={i} style={{ color: "#4ade80" }}>{s}</li>
          ))}
          {(score.explanation?.concerns || []).map((s, i) => (
            <li key={i} style={{ color: "#f87171" }}>{s}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
