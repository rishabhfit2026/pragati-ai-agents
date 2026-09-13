"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AgentRunOut } from "@/lib/types";
import { StatusBadge, Spinner } from "@/components/ui";

export default function AdminPage() {
  const [runs, setRuns] = useState<(AgentRunOut & { tender_id: string })[] | null>(null);

  useEffect(() => {
    api.agentRuns().then(setRuns);
  }, []);

  const failureLike = (runs || []).filter((r) => r.status !== "SUCCESS");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Agent Observability</h1>
        <p style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4 }}>
          Cross-tender view of every agent execution: status, duration, retries, and errors — the same data a
          production on-call engineer would use to diagnose the pipeline.
        </p>
      </div>

      {!runs && (
        <div style={{ display: "flex", gap: 8, color: "var(--muted)" }}>
          <Spinner size={14} /> Loading agent runs…
        </div>
      )}

      {runs && (
        <>
          <div className="card" style={{ padding: 0 }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontWeight: 700, fontSize: 12.5 }}>
              Non-successful runs ({failureLike.length}) — retry / fallback events
            </div>
            <div className="scroll-x">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tender</th>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Retries</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {failureLike.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link href={`/tenders/${r.tender_id}`}>{r.tender_id}</Link>
                      </td>
                      <td>{r.agent_name}</td>
                      <td>
                        <StatusBadge status={r.status} />
                      </td>
                      <td>{r.retries}</td>
                      <td className="mono" style={{ fontSize: 11, color: "#f87171" }}>{r.error || "—"}</td>
                    </tr>
                  ))}
                  {failureLike.length === 0 && (
                    <tr>
                      <td colSpan={5} style={{ textAlign: "center", color: "var(--muted)", padding: 20 }}>
                        No failures recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{ padding: 0 }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontWeight: 700, fontSize: 12.5 }}>
              All runs ({runs.length})
            </div>
            <div className="scroll-x" style={{ maxHeight: 480, overflowY: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tender</th>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Retries</th>
                    <th>Model</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link href={`/tenders/${r.tender_id}`}>{r.tender_id}</Link>
                      </td>
                      <td>{r.agent_name}</td>
                      <td>
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="mono">{r.duration_ms != null ? `${r.duration_ms} ms` : "—"}</td>
                      <td>{r.retries}</td>
                      <td className="mono" style={{ fontSize: 11 }}>{r.model_used || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
