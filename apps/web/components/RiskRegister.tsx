"use client";

import type { RiskOut } from "@/lib/types";
import { SeverityBadge } from "@/components/ui";

export default function RiskRegister({ risks }: { risks: RiskOut[] }) {
  return (
    <div className="card" style={{ padding: 0 }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
        <span style={{ fontSize: 12.5, fontWeight: 700 }}>Risk Register</span>
      </div>
      <div className="scroll-x">
        <table className="data-table">
          <thead>
            <tr>
              <th>Category</th>
              <th style={{ width: "26%" }}>Risk</th>
              <th>Severity</th>
              <th>Probability</th>
              <th>Evidence</th>
              <th>Mitigation</th>
            </tr>
          </thead>
          <tbody>
            {risks.map((r) => (
              <tr key={r.id}>
                <td style={{ fontSize: 11.5, fontWeight: 700, color: "var(--muted)" }}>{r.category}</td>
                <td>{r.description}</td>
                <td>
                  <SeverityBadge level={r.severity} />
                </td>
                <td>
                  <SeverityBadge level={r.probability} />
                </td>
                <td style={{ maxWidth: 260, color: "var(--muted)" }}>{r.evidence}</td>
                <td style={{ maxWidth: 260, color: "var(--muted)" }}>{r.mitigation}</td>
              </tr>
            ))}
            {risks.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "var(--muted)", padding: 24 }}>
                  No material risks identified by the structured analysis.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
