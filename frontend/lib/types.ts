export type EligibilityCode =
  | "Eligible"
  | "Potentially Eligible"
  | "Insufficient Information"
  | "Not Eligible";

export interface ChecklistItem {
  required_key?: string;
  required_label: string;
  status: string;
}

export interface TimelineStage {
  name: string;
  duration: string;
}

export interface SchemeTimeline {
  estimated_days: number;
  stages: TimelineStage[];
}

export interface SchemeSummary {
  id: number;
  title: string;
  description: string;
  benefit_type: string;
  eligibility_status: string;
  eligibility_code?: EligibilityCode;
  eligibility_score: number;
  eligibility_explanation: string;
  missing_information?: string[];
  required_documents?: string[];
  source_url?: string;
  source_note?: string;
}

export interface SchemeDetail extends SchemeSummary {
  department?: string;
  ministry?: string;
  benefit_details?: string;
  readiness_score?: number;
  checklist?: ChecklistItem[];
  timeline?: SchemeTimeline;
  cover_letter?: string;
  disclaimer?: string;
  steps?: string[];
}

export interface CompareScheme extends SchemeDetail {
  benefits: string;
  documents: string[];
  complexity: string;
  timeline_days: number;
  application_steps: string[];
}

export interface AnalyticsAlert {
  type: string;
  severity: string;
  title: string;
  description: string;
}

export interface TimelineEvent {
  date: string;
  title: string;
  type: string;
  completed: boolean;
}

export interface AnalyticsData {
  unlocked_benefit_amount: number;
  estimated_benefit_amount: number;
  benefit_estimate_note?: string;
  schemes_discovered_count: number;
  schemes_evaluated_count: number;
  status_breakdown: Record<EligibilityCode, number>;
  benefit_breakdown: Array<{ name: string; value: number }>;
  pending_documents_count: number;
  documents_count: number;
  upcoming_deadlines_count: number;
  success_rate: number | null;
  applied_count: number;
  approved_count: number;
  alerts: AnalyticsAlert[];
  timeline_events: TimelineEvent[];
}

export interface ProviderStatus {
  requested_provider: string;
  active_provider: string;
  model: string;
  transport: string;
  mode: "live" | "mock" | "unconfigured";
  ready: boolean;
  is_gemma: boolean;
  error: string | null;
  privacy: string;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  agent_name?: string;
}
