"use client";

import { useEffect, useState, use as usePromise } from "react";
import { api, ApiError } from "@/lib/api";
import type { AnalysisOut, AuditEventOut, TenderDetail } from "@/lib/types";
import ExecutiveSummary from "@/components/ExecutiveSummary";
import RequirementsTable from "@/components/RequirementsTable";
import ComplianceMatrix from "@/components/ComplianceMatrix";
import RiskRegister from "@/components/RiskRegister";
import ScorePanel from "@/components/ScorePanel";
import Timeline from "@/components/Timeline";
import AgentRunsPanel from "@/components/AgentRunsPanel";
import ReplayPanel from "@/components/ReplayPanel";
import { Button, Spinner, EmptyState } from "@/components/ui";

const TABS = [
  "Requirements",
  "Compliance",
  "Risks",
  "Score",
  "Timeline",
  "Agent Runs",
  "Replay",
] as const;
type Tab = (typeof TABS)[number];

export default function TenderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = usePromise(params);
  const [tender, setTender] = useState<TenderDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [timeline, setTimeline] = useState<AuditEventOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("Requirements");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const t = await api.getTender(id);
      setTender(t);
      const [a, tl] = await Promise.all([
        api.getAnalysis(id).catch(() => null),
        api.getTimeline(id),
      ]);
      setAnalysis(a);
      setTimeline(tl);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load tender.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--muted)" }}>
        <Spinner /> Loading tender…
      </div>
    );
  }

  if (error || !tender) {
    return <div style={{ color: "#f87171" }}>{error || "Tender not found."}</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {!analysis ? (
        <div className="card" style={{ padding: 24 }}>
          <EmptyState
            title="This tender has not been analyzed yet"
            sub="Run the agent pipeline to generate requirements, capability matches, compliance, risks, and an explainable score."
          />
          <div style={{ textAlign: "center" }}>
            <Button
              onClick={async () => {
                setLoading(true);
                try {
                  const a = await api.analyze(id);
                  setAnalysis(a);
                  const tl = await api.getTimeline(id);
                  setTimeline(tl);
                } catch (e) {
                  setError(e instanceof ApiError ? e.message : "Analysis failed.");
                } finally {
                  setLoading(false);
                }
              }}
            >
              Run Analysis
            </Button>
          </div>
        </div>
      ) : (
        <>
          <ExecutiveSummary
            tender={tender}
            analysis={analysis}
            onOverride={async (a) => {
              setAnalysis(a);
              setTimeline(await api.getTimeline(id));
            }}
          />

          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ display: "flex", gap: 4, background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, padding: 4 }}>
              {TABS.map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    fontSize: 12.5,
                    fontWeight: 600,
                    padding: "7px 14px",
                    borderRadius: 6,
                    background: tab === t ? "var(--accent-dim)" : "transparent",
                    color: tab === t ? "#fff" : "var(--muted)",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
              <a href={api.reportUrl(tender.id)} target="_blank" rel="noreferrer">
                <Button variant="ghost">View Report</Button>
              </a>
              <a href={api.reportPdfUrl(tender.id)}>
                <Button variant="ghost">Download PDF</Button>
              </a>
            </div>
          </div>

          {tab === "Requirements" && <RequirementsTable requirements={analysis.requirements} />}
          {tab === "Compliance" && <ComplianceMatrix items={analysis.compliance_items} />}
          {tab === "Risks" && <RiskRegister risks={analysis.risks} />}
          {tab === "Score" && <ScorePanel score={analysis.score} />}
          {tab === "Timeline" && <Timeline events={timeline} />}
          {tab === "Agent Runs" && <AgentRunsPanel runs={analysis.agent_runs} />}
          {tab === "Replay" && (
            <ReplayPanel
              tenderId={tender.id}
              onReplayed={async () => {
                const a = await api.getAnalysis(id);
                setAnalysis(a);
                const tl = await api.getTimeline(id);
                setTimeline(tl);
              }}
            />
          )}
        </>
      )}
    </div>
  );
}
