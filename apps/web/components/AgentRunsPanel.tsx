"use client";

import type { AgentRunOut } from "@/lib/types";
import { StatusBadge } from "@/components/ui";

export default function AgentRunsPanel({ runs }: { runs: AgentRunOut[] }) {
  return (
    <div className="card" style={{ padding: 0 }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
        <span style={{ fontSize: 12.5, fontWeight: 700 }}>Agent Run — Observability</span>
      </div>
      <div className="scroll-x">
        <table className="data-table">
          <thead>
            <tr>
              <th>Agent</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Retries</th>
              <th>Model</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td style={{ fontWeight: 600 }}>{r.agent_name}</td>
                <td>
                  <StatusBadge status={r.status} />
                </td>
                <td className="mono">{r.duration_ms != null ? `${r.duration_ms} ms` : "—"}</td>
                <td>{r.retries}</td>
                <td className="mono" style={{ fontSize: 11.5 }}>{r.model_used || "—"}</td>
                <td style={{ color: r.error ? "#f87171" : "var(--muted)", fontSize: 12 }}>
                  {r.error || r.output_summary || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
