"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ReplayComparison } from "@/lib/types";
import { Button, RecBadge, Spinner } from "@/components/ui";

export default function ReplayPanel({ tenderId, onReplayed }: { tenderId: string; onReplayed?: () => void }) {
  const [scoringVersion, setScoringVersion] = useState("score-v2");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReplayComparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runReplay() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.replay(tenderId, { scoring_version: scoringVersion });
      setResult(res);
      onReplayed?.();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Replay failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ padding: 18 }}>
      <div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>
        Replay Analysis
      </div>
      <p style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 14, maxWidth: 640 }}>
        Re-run the full pipeline on the same source document with a different scoring configuration, and compare the
        result against the current analysis. Useful for validating scoring-policy changes before rolling them out.
      </p>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: "var(--muted)" }}>Scoring version</label>
        <select
          value={scoringVersion}
          onChange={(e) => setScoringVersion(e.target.value)}
          style={{ background: "var(--panel-2)", border: "1px solid var(--border)", borderRadius: 5, fontSize: 12, padding: "6px 10px", color: "var(--text)" }}
        >
          <option value="score-v1">score-v1 (default weighting)</option>
          <option value="score-v2">score-v2 (compliance-weighted)</option>
        </select>
        <Button onClick={runReplay} disabled={loading}>
          {loading ? <Spinner size={12} /> : null} Run Replay
        </Button>
      </div>

      {error && <div style={{ color: "#f87171", fontSize: 12.5 }}>{error}</div>}

      {result && (
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div className="card-2" style={{ padding: 14, minWidth: 180 }}>
            <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700 }}>OLD RESULT</div>
            <div style={{ fontSize: 26, fontWeight: 800, marginTop: 4 }}>{result.old_analysis.score.final_score}</div>
            <RecBadge rec={result.old_analysis.decision.final_recommendation} />
          </div>
          <div style={{ fontSize: 20, color: "var(--muted)", alignSelf: "center" }}>→</div>
          <div className="card-2" style={{ padding: 14, minWidth: 180 }}>
            <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700 }}>NEW RESULT</div>
            <div style={{ fontSize: 26, fontWeight: 800, marginTop: 4 }}>{result.new_analysis.score.final_score}</div>
            <RecBadge rec={result.new_analysis.decision.final_recommendation} />
          </div>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700, marginBottom: 6 }}>WHAT CHANGED</div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, display: "flex", flexDirection: "column", gap: 4 }}>
              <li>
                Score {result.diff.score_delta >= 0 ? "increased" : "decreased"} by{" "}
                <b className="mono">{Math.abs(result.diff.score_delta).toFixed(1)}</b> points.
              </li>
              <li>
                Recommendation {result.diff.recommendation_changed ? "changed" : "unchanged"}
                {result.diff.recommendation_changed &&
                  `: ${result.diff.old_recommendation} → ${result.diff.new_recommendation}`}
                .
              </li>
              <li className="mono" style={{ color: "var(--muted)" }}>
                {result.diff.old_config.scoring_version} → {result.diff.new_config.scoring_version}
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
