"use client";

import type { AgentRunOut } from "@/lib/types";
import { StatusBadge, Spinner } from "@/components/ui";

const PIPELINE_STEPS = [
  "Document Intelligence Agent",
  "Requirement Extraction Agent",
  "Capability Matching Agent",
  "Eligibility & Compliance Agent",
  "Risk Analysis Agent",
  "Commercial & Strategic Analysis Agent",
  "Opportunity Scoring Agent",
  "Decision Agent",
];

export default function PipelineView({
  runs,
  running,
}: {
  runs: AgentRunOut[] | null;
  running?: boolean;
}) {
  const byName = new Map((runs || []).map((r) => [r.agent_name, r]));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {PIPELINE_STEPS.map((name, i) => {
        const run = byName.get(name);
        const isLast = i === PIPELINE_STEPS.length - 1;
        return (
          <div key={name} style={{ display: "flex", gap: 14 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 20 }}>
              <div
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  marginTop: 6,
                  background: run
                    ? run.status === "FAILED"
                      ? "#f87171"
                      : run.status === "PARTIAL"
                      ? "#fbbf24"
                      : "#4ade80"
                    : running
                    ? "#3b82f6"
                    : "var(--border)",
                  flexShrink: 0,
                }}
              />
              {!isLast && <div style={{ width: 2, flex: 1, background: "var(--border)", minHeight: 28 }} />}
            </div>
            <div style={{ paddingBottom: 20, flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{name}</span>
                {run ? (
                  <StatusBadge status={run.status} />
                ) : running ? (
                  <Spinner size={12} />
                ) : (
                  <span style={{ fontSize: 11, color: "var(--muted)" }}>pending</span>
                )}
              </div>
              {run && (
                <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 3, display: "flex", gap: 12 }}>
                  <span>{run.duration_ms != null ? `${run.duration_ms}ms` : "—"}</span>
                  {run.retries > 0 && <span style={{ color: "#fbbf24" }}>{run.retries} retry(ies)</span>}
                  {run.model_used && <span className="mono">{run.model_used}</span>}
                </div>
              )}
              {run?.output_summary && (
                <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2 }}>{run.output_summary}</div>
              )}
              {run?.error && (
                <div style={{ fontSize: 11, color: "#f87171", marginTop: 2 }} className="mono">
                  {run.error}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
