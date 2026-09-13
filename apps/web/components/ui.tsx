import React from "react";

export function RecBadge({ rec }: { rec: string | null | undefined }) {
  if (!rec) return <span className="badge" style={{ background: "#223049", color: "#8a97ac" }}>PENDING</span>;
  const map: Record<string, { bg: string; fg: string; label: string }> = {
    PURSUE: { bg: "rgba(34,197,94,0.15)", fg: "#4ade80", label: "PURSUE" },
    REVIEW: { bg: "rgba(245,158,11,0.15)", fg: "#fbbf24", label: "REVIEW" },
    DO_NOT_PURSUE: { bg: "rgba(239,68,68,0.15)", fg: "#f87171", label: "DO NOT PURSUE" },
  };
  const s = map[rec] || map.REVIEW;
  return (
    <span className="badge" style={{ background: s.bg, color: s.fg }}>
      {s.label}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; fg: string }> = {
    MATCH: { bg: "rgba(34,197,94,0.15)", fg: "#4ade80" },
    PARTIAL_MATCH: { bg: "rgba(59,130,246,0.15)", fg: "#60a5fa" },
    UNKNOWN: { bg: "rgba(245,158,11,0.15)", fg: "#fbbf24" },
    GAP: { bg: "rgba(239,68,68,0.15)", fg: "#f87171" },
    SUCCESS: { bg: "rgba(34,197,94,0.15)", fg: "#4ade80" },
    PARTIAL: { bg: "rgba(245,158,11,0.15)", fg: "#fbbf24" },
    FAILED: { bg: "rgba(239,68,68,0.15)", fg: "#f87171" },
    RUNNING: { bg: "rgba(59,130,246,0.15)", fg: "#60a5fa" },
    ANALYZED: { bg: "rgba(34,197,94,0.15)", fg: "#4ade80" },
    ANALYZING: { bg: "rgba(59,130,246,0.15)", fg: "#60a5fa" },
    UPLOADED: { bg: "rgba(148,163,184,0.15)", fg: "#94a3b8" },
  };
  const s = map[status] || { bg: "rgba(148,163,184,0.15)", fg: "#94a3b8" };
  return (
    <span className="badge" style={{ background: s.bg, color: s.fg }}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function SeverityBadge({ level }: { level: string }) {
  const map: Record<string, { bg: string; fg: string }> = {
    HIGH: { bg: "rgba(239,68,68,0.15)", fg: "#f87171" },
    MEDIUM: { bg: "rgba(245,158,11,0.15)", fg: "#fbbf24" },
    LOW: { bg: "rgba(148,163,184,0.15)", fg: "#94a3b8" },
  };
  const s = map[level] || map.LOW;
  return (
    <span className="badge" style={{ background: s.bg, color: s.fg }}>
      {level}
    </span>
  );
}

export function FitBadge({ fit, invert = false }: { fit: string | null | undefined; invert?: boolean }) {
  // For "Fit": High is good (green), Low is bad (red).
  // For "Risk" (invert=true): High is bad (red), Low is good (green) — same
  // labels, opposite meaning, so the color scale must flip.
  const scale: Record<string, { bg: string; fg: string }> = {
    High: { bg: "rgba(34,197,94,0.15)", fg: "#4ade80" },
    Medium: { bg: "rgba(245,158,11,0.15)", fg: "#fbbf24" },
    Low: { bg: "rgba(239,68,68,0.15)", fg: "#f87171" },
  };
  const key = fit && invert ? (fit === "High" ? "Low" : fit === "Low" ? "High" : fit) : fit;
  const s = (key && scale[key]) || { bg: "rgba(148,163,184,0.15)", fg: "#94a3b8" };
  return (
    <span className="badge" style={{ background: s.bg, color: s.fg }}>
      {fit || "—"}
    </span>
  );
}

export function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="card" style={{ padding: "16px 18px" }}>
      <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--muted)", textTransform: "uppercase", fontWeight: 600 }}>
        {label}
      </div>
      <div style={{ fontSize: 30, fontWeight: 700, marginTop: 6, color: accent || "var(--text)" }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export function ScoreDial({ score, size = 96 }: { score: number | null | undefined; size?: number }) {
  const v = score ?? 0;
  const color = v >= 75 ? "#4ade80" : v >= 55 ? "#fbbf24" : "#f87171";
  const circumference = 2 * Math.PI * 42;
  const offset = circumference - (v / 100) * circumference;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="42" fill="none" stroke="var(--border)" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ fontSize: size / 3.4, fontWeight: 800, color }}>{score == null ? "—" : Math.round(score)}</div>
        <div style={{ fontSize: 9, color: "var(--muted)", marginTop: -2 }}>/ 100</div>
      </div>
    </div>
  );
}

export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      style={{ animation: "spin 0.8s linear infinite" }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle cx="12" cy="12" r="10" stroke="var(--border)" strokeWidth="3" fill="none" />
      <path d="M12 2 a10 10 0 0 1 10 10" stroke="var(--accent)" strokeWidth="3" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export function EmptyState({ title, sub }: { title: string; sub?: string }) {
  return (
    <div style={{ padding: "48px 16px", textAlign: "center", color: "var(--muted)" }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>{title}</div>
      {sub && <div style={{ fontSize: 12.5, marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

export function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
      {pct}%
    </span>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
  title,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
  title?: string;
}) {
  const base: React.CSSProperties = {
    padding: "8px 14px",
    borderRadius: 6,
    fontSize: 12.5,
    fontWeight: 600,
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    border: "1px solid transparent",
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
  };
  const variants: Record<string, React.CSSProperties> = {
    primary: { background: "var(--accent)", color: "#fff" },
    ghost: { background: "transparent", color: "var(--text)", border: "1px solid var(--border)" },
    danger: { background: "rgba(239,68,68,0.15)", color: "#f87171", border: "1px solid rgba(239,68,68,0.3)" },
  };
  return (
    <button
      type={type}
      title={title}
      onClick={onClick}
      disabled={disabled}
      style={{ ...base, ...variants[variant] }}
    >
      {children}
    </button>
  );
}
