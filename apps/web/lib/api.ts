const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let message = text;
    try {
      message = JSON.parse(text).detail || text;
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, message || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  dashboardStats: () => request<import("./types").DashboardStats>("/api/dashboard/stats"),
  listTenders: () => request<import("./types").TenderSummary[]>("/api/tenders"),
  getTender: (id: string) => request<import("./types").TenderDetail>(`/api/tenders/${id}`),
  getTimeline: (id: string) => request<import("./types").AuditEventOut[]>(`/api/tenders/${id}/timeline`),
  listAnalyses: (id: string) => request<import("./types").AnalysisOut[]>(`/api/tenders/${id}/analyses`),
  getAnalysis: (id: string, analysisId?: string) =>
    request<import("./types").AnalysisOut>(
      `/api/tenders/${id}/analysis${analysisId ? `?analysis_id=${analysisId}` : ""}`
    ),
  analyze: (id: string, simulateFailure?: string) =>
    request<import("./types").AnalysisOut>(`/api/tenders/${id}/analyze`, {
      method: "POST",
      body: JSON.stringify({ simulate_failure: simulateFailure || null }),
    }),
  replay: (id: string, config: Record<string, string | undefined>) =>
    request<import("./types").ReplayComparison>(`/api/tenders/${id}/replay`, {
      method: "POST",
      body: JSON.stringify(config),
    }),
  overrideDecision: (id: string, finalRecommendation: string, reason: string, actor: string) =>
    request<import("./types").AnalysisOut>(`/api/tenders/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ final_recommendation: finalRecommendation, reason, actor }),
    }),
  agentRuns: (params?: { tender_id?: string }) =>
    request<(import("./types").AgentRunOut & { tender_id: string })[]>(
      `/api/agents/runs${params?.tender_id ? `?tender_id=${params.tender_id}` : ""}`
    ),
  loadDemo: () => request<{ loaded: string[]; count: number }>("/api/demo/load", { method: "POST" }),
  clearDemo: () => request<{ status: string }>("/api/demo/clear", { method: "POST" }),
  search: (q: string) =>
    request<{ query: string; results: { tender_id: string; title: string; score: number; matched_fields: string[] }[] }>(
      `/api/search?q=${encodeURIComponent(q)}`
    ),
  knowledgeBase: () => request<Record<string, unknown>>("/api/knowledge"),
  reportUrl: (id: string) => `${API_URL}/api/tenders/${id}/report.html`,
  reportPdfUrl: (id: string) => `${API_URL}/api/tenders/${id}/report.pdf`,
  async upload(file: File): Promise<import("./types").TenderDetail> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/tenders/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      let message = text;
      try {
        message = JSON.parse(text).detail || text;
      } catch {
        /* not json */
      }
      throw new ApiError(res.status, message || `Upload failed (${res.status})`);
    }
    return res.json();
  },
};
