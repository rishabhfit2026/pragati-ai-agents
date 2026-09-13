"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { DashboardStats, TenderSummary } from "@/lib/types";
import { StatCard, RecBadge, FitBadge, StatusBadge, Button, Spinner, EmptyState } from "@/components/ui";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tenders, setTenders] = useState<TenderSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingDemo, setLoadingDemo] = useState(false);

  const [recFilter, setRecFilter] = useState<string>("ALL");
  const [minScore, setMinScore] = useState<number>(0);
  const [sortKey, setSortKey] = useState<"score" | "deadline">("score");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [s, t] = await Promise.all([api.dashboardStats(), api.listTenders()]);
      setStats(s);
      setTenders(t);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to reach the API. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleLoadDemo() {
    setLoadingDemo(true);
    try {
      await api.loadDemo();
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load demo data.");
    } finally {
      setLoadingDemo(false);
    }
  }

  const filtered = useMemo(() => {
    if (!tenders) return [];
    let list = tenders.filter((t) => (t.final_score ?? 0) >= minScore);
    if (recFilter !== "ALL") list = list.filter((t) => t.final_recommendation === recFilter);
    list = [...list].sort((a, b) => {
      if (sortKey === "score") return (b.final_score ?? -1) - (a.final_score ?? -1);
      return (a.submission_deadline || "").localeCompare(b.submission_deadline || "");
    });
    return list;
  }, [tenders, recFilter, minScore, sortKey]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Opportunity Center</h1>
          <p style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4 }}>
            AI-analyzed tender opportunities, ranked by explainable fit score.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Button variant="ghost" onClick={load}>
            Refresh
          </Button>
          <Link href="/upload">
            <Button variant="ghost">+ Upload Tender</Button>
          </Link>
          <Button onClick={handleLoadDemo} disabled={loadingDemo}>
            {loadingDemo ? <Spinner size={12} /> : null} Load Demo
          </Button>
        </div>
      </div>

      {error && (
        <div className="card" style={{ padding: 14, borderColor: "rgba(239,68,68,0.4)", color: "#f87171", fontSize: 13 }}>
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        <StatCard label="Total Opportunities" value={stats?.total_opportunities ?? (loading ? "…" : 0)} />
        <StatCard label="High Priority" value={stats?.high_priority ?? (loading ? "…" : 0)} accent="#4ade80" sub="AI Recommendation: PURSUE" />
        <StatCard label="Review Required" value={stats?.review_required ?? (loading ? "…" : 0)} accent="#fbbf24" sub="Needs human decision" />
        <StatCard label="Low Fit" value={stats?.low_fit ?? (loading ? "…" : 0)} accent="#f87171" sub="AI Recommendation: DO NOT PURSUE" />
        <StatCard label="Avg. Opportunity Score" value={stats?.average_score ?? (loading ? "…" : 0)} sub={`${stats?.upcoming_deadlines ?? 0} upcoming deadlines`} />
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "12px 16px",
            borderBottom: "1px solid var(--border)",
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontSize: 12.5, fontWeight: 700 }}>Opportunities</span>
          <div style={{ display: "flex", gap: 6, marginLeft: 8 }}>
            {["ALL", "PURSUE", "REVIEW", "DO_NOT_PURSUE"].map((r) => (
              <button
                key={r}
                onClick={() => setRecFilter(r)}
                style={{
                  fontSize: 11,
                  padding: "5px 10px",
                  borderRadius: 5,
                  border: "1px solid var(--border)",
                  background: recFilter === r ? "var(--accent-dim)" : "transparent",
                  color: recFilter === r ? "#fff" : "var(--muted)",
                  fontWeight: 600,
                }}
              >
                {r.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <label style={{ fontSize: 11, color: "var(--muted)" }}>Min score</label>
            <input
              type="range"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
            />
            <span className="mono" style={{ fontSize: 11, width: 24 }}>
              {minScore}
            </span>
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as "score" | "deadline")}
              style={{ background: "var(--panel-2)", border: "1px solid var(--border)", borderRadius: 5, fontSize: 11, padding: "5px 8px", color: "var(--text)" }}
            >
              <option value="score">Sort: Score</option>
              <option value="deadline">Sort: Deadline</option>
            </select>
          </div>
        </div>

        <div className="scroll-x">
          <table className="data-table">
            <thead>
              <tr>
                <th>Tender</th>
                <th>Customer</th>
                <th>Score</th>
                <th>Fit</th>
                <th>Risk</th>
                <th>Deadline</th>
                <th>Recommendation</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loading &&
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 8 }).map((__, j) => (
                      <td key={j}>
                        <div className="skeleton" style={{ height: 14, width: "80%" }} />
                      </td>
                    ))}
                  </tr>
                ))}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={8}>
                    <EmptyState
                      title="No opportunities yet"
                      sub='Click "Load Demo" to populate the Opportunity Center with sample tenders, or upload a real tender PDF.'
                    />
                  </td>
                </tr>
              )}
              {filtered.map((t) => (
                <tr key={t.id}>
                  <td style={{ maxWidth: 320 }}>
                    <Link href={`/tenders/${t.id}`} style={{ fontWeight: 600, color: "var(--text)" }}>
                      {t.title || "(untitled tender)"}
                    </Link>
                    {t.is_demo && (
                      <span className="badge" style={{ marginLeft: 8, background: "rgba(148,163,184,0.15)", color: "#94a3b8" }}>
                        DEMO DATA
                      </span>
                    )}
                    <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{t.tender_number}</div>
                  </td>
                  <td style={{ maxWidth: 200 }}>{t.issuing_organization || "—"}</td>
                  <td className="mono" style={{ fontWeight: 700 }}>
                    {t.final_score != null ? t.final_score.toFixed(1) : "—"}
                  </td>
                  <td>
                    <FitBadge fit={t.fit_label} />
                  </td>
                  <td>
                    <FitBadge fit={t.risk_label} invert />
                  </td>
                  <td style={{ fontSize: 12 }}>{t.submission_deadline || "—"}</td>
                  <td>
                    <RecBadge rec={t.final_recommendation} />
                  </td>
                  <td>
                    <StatusBadge status={t.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
