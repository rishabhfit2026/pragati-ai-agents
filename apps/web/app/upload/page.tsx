"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { AnalysisOut, TenderDetail } from "@/lib/types";
import { Button, Spinner } from "@/components/ui";
import PipelineView from "@/components/PipelineView";

const FAILURE_MODES = [
  { value: "", label: "None (normal run)" },
  { value: "OCR_TIMEOUT", label: "OCR_TIMEOUT — scanned page OCR fails once" },
  { value: "LLM_TIMEOUT", label: "LLM_TIMEOUT — extraction model call times out once" },
  { value: "INVALID_JSON", label: "INVALID_JSON — extraction returns malformed data once" },
  { value: "TOOL_ERROR", label: "TOOL_ERROR — knowledge base lookup fails once" },
];

export default function UploadPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [tender, setTender] = useState<TenderDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [devMode, setDevMode] = useState(false);
  const [failureMode, setFailureMode] = useState("");

  async function handleFile(file: File) {
    setError(null);
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are accepted.");
      return;
    }
    setUploading(true);
    setTender(null);
    setAnalysis(null);
    try {
      const t = await api.upload(file);
      setTender(t);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleAnalyze() {
    if (!tender) return;
    setAnalyzing(true);
    setError(null);
    try {
      const a = await api.analyze(tender.id, failureMode || undefined);
      setAnalysis(a);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 860 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Upload Tender</h1>
        <p style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4 }}>
          Upload a tender/RFP PDF to run it through the full agent pipeline: extraction, requirement structuring,
          capability matching, compliance analysis, risk analysis, and explainable scoring.
        </p>
      </div>

      {!tender && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleFile(file);
          }}
          onClick={() => inputRef.current?.click()}
          className="card"
          style={{
            padding: 48,
            textAlign: "center",
            cursor: "pointer",
            borderStyle: "dashed",
            borderColor: dragOver ? "var(--accent)" : "var(--border)",
            background: dragOver ? "rgba(59,130,246,0.06)" : "var(--panel)",
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            hidden
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          {uploading ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <Spinner size={22} />
              <span style={{ fontSize: 13, color: "var(--muted)" }}>Uploading…</span>
            </div>
          ) : (
            <>
              <div style={{ fontSize: 14, fontWeight: 600 }}>Drag & drop a tender PDF here</div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>or click to browse — PDF only, max 25MB</div>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="card" style={{ padding: 14, borderColor: "rgba(239,68,68,0.4)", color: "#f87171", fontSize: 13 }}>
          {error}
        </div>
      )}

      {tender && (
        <div className="card" style={{ padding: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ fontSize: 10.5, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Document Received
              </div>
              <div style={{ fontSize: 15, fontWeight: 700, marginTop: 4 }}>{tender.filename}</div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }} className="mono">
                sha256:{tender.file_hash.slice(0, 16)}…
                {tender.page_count > 0 && <> &nbsp;•&nbsp; {tender.page_count} page(s)</>}
              </div>
            </div>
            <Button
              variant="ghost"
              onClick={() => {
                setTender(null);
                setAnalysis(null);
              }}
            >
              Upload different file
            </Button>
          </div>

          {!analysis && (
            <div style={{ marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
              <button
                onClick={() => setDevMode((d) => !d)}
                style={{ fontSize: 11, color: "var(--muted)", background: "none", marginBottom: 10 }}
              >
                {devMode ? "▾" : "▸"} Developer options (failure simulation)
              </button>
              {devMode && (
                <div style={{ marginBottom: 14 }}>
                  <label style={{ fontSize: 11.5, color: "var(--muted)", display: "block", marginBottom: 4 }}>
                    Simulate an agent failure to demonstrate retry → fallback → success
                  </label>
                  <select
                    value={failureMode}
                    onChange={(e) => setFailureMode(e.target.value)}
                    style={{
                      background: "var(--panel-2)",
                      border: "1px solid var(--border)",
                      borderRadius: 5,
                      fontSize: 12,
                      padding: "6px 10px",
                      color: "var(--text)",
                      width: "100%",
                      maxWidth: 420,
                    }}
                  >
                    {FAILURE_MODES.map((f) => (
                      <option key={f.value} value={f.value}>
                        {f.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <Button onClick={handleAnalyze} disabled={analyzing}>
                {analyzing ? <Spinner size={12} /> : null} Start Analysis
              </Button>
            </div>
          )}

          {(analyzing || analysis) && (
            <div style={{ marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
              <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 12 }}>Agent Pipeline</div>
              <PipelineView runs={analysis?.agent_runs || null} running={analyzing} />
            </div>
          )}

          {analysis && (
            <div style={{ marginTop: 8, display: "flex", gap: 10 }}>
              <Button onClick={() => router.push(`/tenders/${tender.id}`)}>View Full Analysis →</Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
