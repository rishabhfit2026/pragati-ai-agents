"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Opportunity Center" },
  { href: "/upload", label: "Upload Tender" },
  { href: "/knowledge", label: "Knowledge Base" },
  { href: "/admin", label: "Agent Observability" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [q, setQ] = useState("");

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 232,
          flexShrink: 0,
          borderRight: "1px solid var(--border)",
          background: "var(--panel)",
          display: "flex",
          flexDirection: "column",
          position: "sticky",
          top: 0,
          height: "100vh",
        }}
      >
        <div style={{ padding: "18px 18px 14px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: "0.02em" }}>PRAGATI</div>
          <div style={{ fontSize: 10.5, color: "var(--muted)", marginTop: 2, letterSpacing: "0.03em" }}>
            OPPORTUNITY INTELLIGENCE
          </div>
        </div>
        <nav style={{ padding: 10, display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
          {NAV.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  padding: "9px 12px",
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  color: active ? "#fff" : "var(--muted)",
                  background: active ? "var(--accent-dim)" : "transparent",
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div style={{ padding: 14, borderTop: "1px solid var(--border)" }}>
          <div
            style={{
              fontSize: 10.5,
              lineHeight: 1.5,
              color: "var(--muted)",
              background: "rgba(245,158,11,0.08)",
              border: "1px solid rgba(245,158,11,0.25)",
              borderRadius: 6,
              padding: "8px 10px",
            }}
          >
            <b style={{ color: "#fbbf24" }}>PROTOTYPE</b> — uses only public Pragati Defence information and
            clearly-labelled synthetic demo data. Not connected to any confidential/internal system.
          </div>
        </div>
      </aside>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header
          style={{
            height: 56,
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            gap: 16,
            padding: "0 20px",
            position: "sticky",
            top: 0,
            background: "rgba(10,15,28,0.85)",
            backdropFilter: "blur(6px)",
            zIndex: 10,
          }}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (q.trim()) router.push(`/search?q=${encodeURIComponent(q.trim())}`);
            }}
            style={{ flex: 1, maxWidth: 480 }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search tenders, requirements, certifications, risks..."
              style={{
                width: "100%",
                background: "var(--panel-2)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "7px 12px",
                fontSize: 12.5,
                color: "var(--text)",
                outline: "none",
              }}
            />
          </form>
          <div style={{ marginLeft: "auto", fontSize: 11.5, color: "var(--muted)" }}>
            Business Development &nbsp;•&nbsp; Demo Workspace
          </div>
        </header>
        <main style={{ flex: 1, padding: 24 }}>{children}</main>
      </div>
    </div>
  );
}
