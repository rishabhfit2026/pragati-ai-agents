"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui";

interface Product {
  id: string;
  name: string;
  category: string;
  confidence?: number;
  unknowns?: string[];
  [key: string]: unknown;
}

interface KB {
  company: Record<string, unknown>;
  products: Product[];
  capabilities: Record<string, unknown>;
}

function renderValue(v: unknown): string {
  if (v == null) return "—";
  if (Array.isArray(v)) return v.map((x) => (typeof x === "object" ? JSON.stringify(x) : String(x))).join("; ");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export default function KnowledgeBasePage() {
  const [kb, setKb] = useState<KB | null>(null);

  useEffect(() => {
    api.knowledgeBase().then((d) => setKb(d as unknown as KB));
  }, []);

  if (!kb) {
    return (
      <div style={{ display: "flex", gap: 8, color: "var(--muted)" }}>
        <Spinner size={14} /> Loading knowledge base…
      </div>
    );
  }

  const categories = Array.from(new Set(kb.products.map((p) => p.category)));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Pragati Capability &amp; Product Knowledge Base</h1>
        <p style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4, maxWidth: 720 }}>
          Sourced entirely from Pragati Defence Systems&apos; public website (pragatidefence.com). No confidential or
          internal specifications are included. Fields not published are explicitly marked as unverified rather than
          assumed.
        </p>
      </div>

      <div className="card" style={{ padding: 16 }}>
        <div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 10 }}>Company</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
          {Object.entries(kb.company)
            .filter(([k]) => !k.startsWith("_"))
            .map(([k, v]) => (
              <div key={k}>
                <div style={{ fontSize: 10.5, color: "var(--muted)" }}>{k.replace(/_/g, " ")}</div>
                <div style={{ fontSize: 12.5, marginTop: 2, color: String(v).includes("Unknown") ? "#fbbf24" : "var(--text)" }}>
                  {renderValue(v)}
                </div>
              </div>
            ))}
        </div>
      </div>

      {categories.map((cat) => (
        <div key={cat} className="card" style={{ padding: 0 }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontWeight: 700, fontSize: 12.5 }}>{cat}</div>
          <div className="scroll-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Key Specs</th>
                  <th>Unverified</th>
                </tr>
              </thead>
              <tbody>
                {kb.products
                  .filter((p) => p.category === cat)
                  .map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 700 }}>{p.name}</td>
                      <td style={{ maxWidth: 480, fontSize: 12, color: "var(--muted)" }}>
                        {Object.entries(p)
                          .filter(([k]) => !["id", "name", "category", "confidence", "unknowns", "_source"].includes(k))
                          .slice(0, 4)
                          .map(([k, v]) => `${k.replace(/_/g, " ")}: ${renderValue(v)}`)
                          .join(" · ")}
                      </td>
                      <td style={{ fontSize: 11.5, color: "#fbbf24", maxWidth: 260 }}>
                        {(p.unknowns || []).join("; ") || "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
