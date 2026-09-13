export type Recommendation = "PURSUE" | "REVIEW" | "DO_NOT_PURSUE";
export type MatchStatus = "MATCH" | "PARTIAL_MATCH" | "UNKNOWN" | "GAP";
export type ComplianceStatus = "MATCH" | "UNKNOWN" | "GAP";
export type Severity = "LOW" | "MEDIUM" | "HIGH";
export type AgentStatus = "RUNNING" | "SUCCESS" | "PARTIAL" | "FAILED";

export interface TenderSummary {
  id: string;
  title: string | null;
  issuing_organization: string | null;
  tender_number: string | null;
  submission_deadline: string | null;
  product_category: string | null;
  status: string;
  is_demo: boolean;
  uploaded_at: string;
  final_score: number | null;
  final_recommendation: Recommendation | null;
  fit_label: string | null;
  risk_label: string | null;
  active_analysis_id?: string | null;
}

export interface TenderDetail extends TenderSummary {
  filename: string;
  file_hash: string;
  page_count: number;
  issue_date: string | null;
  delivery_deadline: string | null;
  geography: string | null;
  estimated_quantity: string | null;
}

export interface CapabilityMatchOut {
  id: string;
  requirement_id: string;
  status: MatchStatus;
  confidence: number;
  evidence: string;
  kb_reference_id: string | null;
  kb_reference_name: string | null;
}

export interface RequirementOut {
  id: string;
  description: string;
  category: string;
  mandatory: boolean;
  confidence: number;
  source_page: number | null;
  source_section: string | null;
  source_text_snippet: string | null;
  capability_match: CapabilityMatchOut | null;
}

export interface ComplianceItemOut {
  id: string;
  requirement_id: string | null;
  title: string;
  status: ComplianceStatus;
  confidence: number;
  evidence: string;
}

export interface RiskOut {
  id: string;
  category: string;
  description: string;
  severity: Severity;
  probability: Severity;
  evidence: string;
  mitigation: string;
}

export interface AgentRunOut {
  id: string;
  agent_name: string;
  status: AgentStatus;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  retries: number;
  error: string | null;
  model_used: string | null;
  prompt_version: string | null;
  tokens_used: number | null;
  output_summary: string | null;
}

export interface ScoreBreakdown {
  technical_fit: number | null;
  capability_fit: number | null;
  compliance_readiness: number | null;
  strategic_fit: number | null;
  commercial_attractiveness: number | null;
  delivery_feasibility: number | null;
  final_score: number | null;
  weights: Record<string, number>;
  explanation: {
    weights: Record<string, number>;
    scoring_version?: string;
    sub_scores: Record<string, number>;
    strengths: string[];
    concerns: string[];
    strategic_notes: string[];
    commercial_notes: string[];
    delivery_notes: string[];
  } | null;
}

export interface DecisionOut {
  ai_recommendation: Recommendation | null;
  final_recommendation: Recommendation | null;
  decision_reasons: {
    rule_applied: string;
    why: string[];
    concerns: string[];
    immediate_actions: string[];
    critical_gap_count: number;
    unknown_compliance_count: number;
  } | null;
  human_override: boolean;
  override_reason: string | null;
  overridden_by: string | null;
  overridden_at: string | null;
}

export interface AnalysisOut {
  id: string;
  tender_id: string;
  created_at: string;
  status: string;
  llm_provider: string;
  llm_model: string;
  prompt_version: string;
  scoring_version: string;
  is_replay_of: string | null;
  simulated_failure: string | null;
  error: string | null;
  score: ScoreBreakdown;
  decision: DecisionOut;
  requirements: RequirementOut[];
  compliance_items: ComplianceItemOut[];
  risks: RiskOut[];
  agent_runs: AgentRunOut[];
}

export interface AuditEventOut {
  id: string;
  analysis_id: string | null;
  timestamp: string;
  event_type: string;
  description: string;
  actor: string;
  metadata: Record<string, unknown> | null;
}

export interface DashboardStats {
  total_opportunities: number;
  high_priority: number;
  review_required: number;
  low_fit: number;
  new_this_week: number;
  average_score: number;
  upcoming_deadlines: number;
}

export interface ReplayComparison {
  old_analysis: AnalysisOut;
  new_analysis: AnalysisOut;
  diff: {
    score_changed: boolean;
    score_delta: number;
    recommendation_changed: boolean;
    old_score: number | null;
    new_score: number | null;
    old_recommendation: Recommendation | null;
    new_recommendation: Recommendation | null;
    sub_score_changes: Record<string, { old: number; new: number; delta: number }>;
    requirement_count_delta: number;
    gap_count_delta: number;
    old_config: Record<string, string>;
    new_config: Record<string, string>;
  };
}
