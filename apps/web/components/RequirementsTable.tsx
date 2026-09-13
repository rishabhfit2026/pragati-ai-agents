"use client";

import { useState } from "react";
import type { RequirementOut } from "@/lib/types";
import { StatusBadge, ConfidencePill } from "@/components/ui";

const CATEGORIES = [
  "all", "technical", "ballistic", "material", "dimensional", "performance", "certification",
  "testing", "manufacturing", "documentation", "delivery", "financial", "eligibility",
];

export default function RequirementsTable({ requirements }: { requirements: RequirementOut[] }) {
  const [selected, setSelected] = useState<RequirementOut | null>(null);
  const [category, setCategory] = useState("all");
  const [mandatoryOnly, setMandatoryOnly] = useState(false);

  const filtered = requirements.filter(
    (r) => (category === "all" || r.category === category) && (!mandatoryOnly || r.mandatory)
  );

  return (
    <div style={{ display: "flex", gap: 16 }}>
      <div className="card" style={{ flex: 1, padding: 0, minWidth: 0 }}>
        <div style={{ display: "flex", gap: 8, padding: "10px 14px", borderBottom: "1px solid var(--border)", alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={{ background: "var(--panel-2)", border: "1px solid var(--border)", borderRadius: 5, fontSize: 11.5, padding: "5px 8px", color: "var(--text)" }}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c === "all" ? "All categories" : c}
              </option>
            ))}
          </select>
          <label style={{ fontSize: 11.5, color: "var(--muted)", display: "flex", alignItems: "center", gap: 5 }}>
            <input type="checkbox" checked={mandatoryOnly} onChange={(e) => setMandatoryOnly(e.target.checked)} />
            Mandatory only
          </label>
          <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--muted)" }}>{filtered.length} requirement(s)</span>
        </div>
        <div className="scroll-x" style={{ maxHeight: 620, overflowY: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: "40%" }}>Requirement</th>
                <th>Category</th>
                <th>Mandatory</th>
                <th>Confidence</th>
                <th>Page</th>
                <th>Capability Match</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  style={{ cursor: "pointer", background: selected?.id === r.id ? "rgba(59,130,246,0.08)" : undefined }}
                >
                  <td style={{ maxWidth: 420 }}>{r.description}</td>
                  <td style={{ fontSize: 11.5 }}>{r.category}</td>
                  <td style={{ fontSize: 11.5 }}>{r.mandatory ? "Yes" : "No"}</td>
                  <td>
                    <ConfidencePill value={r.confidence} />
                  </td>
                  <td className="mono" style={{ fontSize: 11.5 }}>{r.source_page ?? "—"}</td>
                  <td>{r.capability_match ? <StatusBadge status={r.capability_match.status} /> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card" style={{ width: 340, flexShrink: 0, padding: 16, alignSelf: "flex-start", position: "sticky", top: 76 }}>
        <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", fontWeight: 700, marginBottom: 10 }}>
          Traceability &amp; Evidence
        </div>
        {!selected ? (
          <div style={{ fontSize: 12.5, color: "var(--muted)" }}>Click a requirement row to see its source page, original text, and the AI&apos;s capability-match evidence.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700 }}>REQUIREMENT</div>
              <div style={{ fontSize: 13, marginTop: 3 }}>{selected.description}</div>
            </div>
            <div style={{ display: "flex", gap: 16 }}>
              <div>
                <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700 }}>SOURCE PAGE</div>
                <div className="mono" style={{ fontSize: 13, marginTop: 3 }}>{selected.source_page ?? "—"}</div>
              </div>
              <div>
                <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700 }}>SECTION</div>
                <div style={{ fontSize: 13, marginTop: 3 }}>{selected.source_section ?? "—"}</div>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700 }}>ORIGINAL TEXT SNIPPET</div>
              <div className="card-2 mono" style={{ fontSize: 11.5, marginTop: 4, padding: 10, color: "var(--muted)" }}>
                &ldquo;{selected.source_text_snippet}&rdquo;
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700 }}>EXTRACTION CONFIDENCE</div>
              <div style={{ fontSize: 13, marginTop: 3 }}>{Math.round(selected.confidence * 100)}%</div>
            </div>
            {selected.capability_match && (
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
                <div style={{ fontSize: 10.5, color: "var(--muted)", fontWeight: 700, marginBottom: 6 }}>
                  AI CAPABILITY-MATCH CONCLUSION
                </div>
                <StatusBadge status={selected.capability_match.status} />
                <div style={{ fontSize: 12.5, marginTop: 8 }}>{selected.capability_match.evidence}</div>
                {selected.capability_match.kb_reference_name && (
                  <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 6 }}>
                    Knowledge base reference:{" "}
                    <span className="mono">
                      {selected.capability_match.kb_reference_id} — {selected.capability_match.kb_reference_name}
                    </span>
                  </div>
                )}
                <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 6 }}>
                  Match confidence: {Math.round(selected.capability_match.confidence * 100)}%
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
