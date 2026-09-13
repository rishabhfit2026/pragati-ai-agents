"use client";

import type { AuditEventOut } from "@/lib/types";

export default function Timeline({ events }: { events: AuditEventOut[] }) {
  return (
    <div className="card" style={{ padding: 18 }}>
      <div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, marginBottom: 14, textTransform: "uppercase", letterSpacing: "0.05em" }}>
        Analysis Timeline (Audit Log)
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {events.map((e, i) => (
          <div key={e.id} style={{ display: "flex", gap: 14 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 16 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", marginTop: 5, flexShrink: 0 }} />
              {i < events.length - 1 && <div style={{ width: 2, flex: 1, background: "var(--border)", minHeight: 24 }} />}
            </div>
            <div style={{ paddingBottom: 16 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
                <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
                <span style={{ fontSize: 12, fontWeight: 700 }}>{e.event_type.replace(/_/g, " ")}</span>
                {e.actor !== "system" && (
                  <span className="badge" style={{ background: "rgba(59,130,246,0.15)", color: "#60a5fa" }}>{e.actor}</span>
                )}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 3 }}>{e.description}</div>
            </div>
          </div>
        ))}
        {events.length === 0 && <div style={{ color: "var(--muted)", fontSize: 12.5 }}>No audit events yet.</div>}
      </div>
    </div>
  );
}
