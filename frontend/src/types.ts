// Mirrors the FastAPI /analyse response (app/schemas.py + pipeline output).

export interface CategoryStat {
  total: number;
  count: number;
  percentage: number;
}

export interface InflowBreakdown {
  total_inflow: number;
  categories: Record<string, CategoryStat>;
}

export interface TxnView {
  date: string;
  amount: number;
  counterparty: string;
  description: string;
}

export interface RoundNumberBias {
  detected: boolean;
  value_share: number;
  count: number;
  count_share: number;
  flagged_value: number;
  divisor: number;
  expected_by_chance: number;
  evidence: TxnView[];
}

export interface RepeatCluster {
  amount: number;
  count: number;
  total: number;
  counterparties: string[];
}

export interface IdenticalRepeats {
  detected: boolean;
  value_share: number;
  repeated_clusters: number;
  repeated_value: number;
  min_count: number;
  evidence: RepeatCluster[];
}

export interface MonthEntry {
  month: string;
  inflow_total: number;
  last_days_total: number;
  last_days_count: number;
  last_days_share: number;
}

export interface EndOfMonthSpike {
  detected: boolean;
  value_share: number;
  window_days: number;
  expected_share: number;
  last_days_value: number;
  last_days_count: number;
  by_month: MonthEntry[];
}

export interface RelatedCounterparty {
  counterparty: string;
  label: string;
  total: number;
  count: number;
}

export interface RelatedPartyFlows {
  detected: boolean;
  value_share: number;
  count: number;
  flagged_value: number;
  counterparties: RelatedCounterparty[];
}

export interface PatternAnomalies {
  round_number_bias: RoundNumberBias;
  identical_amount_repeats: IdenticalRepeats;
  end_of_month_spike: EndOfMonthSpike;
  suspected_intercompany_or_related_party_flows: RelatedPartyFlows;
}

export interface ScoreComponent {
  name: string;
  penalty: number;
  max_penalty: number;
  driver_share: number;
  explanation: string;
}

export interface ScoreBreakdown {
  score: number;
  total_penalty: number;
  components: ScoreComponent[];
}

export type Decision =
  | "trust_reported_revenue"
  | "verify_with_vat_returns"
  | "decline";

export interface Recommendation {
  decision: Decision;
  justification: string;
}

export interface Period {
  start: string;
  end: string;
  months: number;
}

export interface Meta {
  currency: string;
  rows_total: number;
  rows_parsed: number;
  rows_skipped: number;
  skipped_examples: unknown[];
  period: Period;
  inflow_transactions: number;
  outflow_transactions: number;
  total_inflow: number;
  total_outflow: number;
  annualised_inflow_estimate: number;
  borrower_profile: { related_tokens: string[]; owner_tokens: string[] };
}

export interface MonthlySeriesEntry {
  month: string;
  total: number;
  count: number;
}

export interface TopCounterparty {
  counterparty: string;
  category: string;
  total: number;
  count: number;
}

export interface Report {
  monthly_inflow_series: MonthlySeriesEntry[];
  top_inflow_counterparties: TopCounterparty[];
  sample_flagged_transactions: {
    round_number: TxnView[];
    related_party: TxnView[];
  };
  notes: string[];
}

export interface AnalyseResponse {
  meta: Meta;
  inflow_breakdown: InflowBreakdown;
  pattern_anomalies: PatternAnomalies;
  revenue_quality_score: number;
  score_breakdown: ScoreBreakdown;
  recommendation: Recommendation;
  report: Report;
}
