"use client";

import type { ComplianceItemOut } from "@/lib/types";
import { StatusBadge, ConfidencePill } from "@/components/ui";

export default function ComplianceMatrix({ items }: { items: ComplianceItemOut[] }) {
  const gaps = items.filter((i) => i.status === "GAP").length;
  const unknowns = items.filter((i) => i.status === "UNKNOWN").length;
  const matches = items.filter((i) => i.status === "MATCH").length;

  return (
    <div className="card" style={{ padding: 0 }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", gap: 18, alignItems: "center" }}>
        <span style={{ fontSize: 12.5, fontWeight: 700 }}>Compliance Matrix</span>
        <span style={{ fontSize: 11.5, color: "var(--muted)" }}>{matches} match · {unknowns} unverified · {gaps} gap</span>
        <span style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--muted)", maxWidth: 420, textAlign: "right" }}>
          Conservative by design — an unverified fact is never upgraded to a pass.
        </span>
      </div>
      <div className="scroll-x">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: "22%" }}>Requirement</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td style={{ fontWeight: 600 }}>{i.title}</td>
                <td>
                  <StatusBadge status={i.status} />
                </td>
                <td>
                  <ConfidencePill value={i.confidence} />
                </td>
                <td style={{ maxWidth: 480, color: "var(--muted)" }}>{i.evidence}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", color: "var(--muted)", padding: 24 }}>
                  No certification/eligibility/documentation requirements were detected in this tender.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
