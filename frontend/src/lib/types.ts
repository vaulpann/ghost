export type Registry = "npm" | "pypi" | "github";
export type Priority = "critical" | "high" | "medium" | "low";
export type RiskLevel = "none" | "low" | "medium" | "high" | "critical";
export type AnalysisStatus =
  | "pending"
  | "triage_in_progress"
  | "triage_complete"
  | "deep_analysis_in_progress"
  | "deep_analysis_complete"
  | "synthesis_in_progress"
  | "complete"
  | "failed"
  | "skipped";

export interface Package {
  id: string;
  name: string;
  registry: Registry;
  registry_url: string | null;
  repository_url: string | null;
  description: string | null;
  latest_known_version: string | null;
  monitoring_enabled: boolean;
  priority: Priority;
  weekly_downloads: number | null;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Version {
  id: string;
  package_id: string;
  version_string: string;
  previous_version_string: string | null;
  published_at: string | null;
  tarball_url: string | null;
  diff_size_bytes: number | null;
  diff_file_count: number | null;
  detection_method: string;
  created_at: string;
  has_analysis: boolean;
  risk_level: RiskLevel | null;
  risk_score: number | null;
}

export interface Analysis {
  id: string;
  version_id: string;
  status: AnalysisStatus;
  triage_result: Record<string, unknown> | null;
  triage_flagged: boolean | null;
  triage_model: string | null;
  triage_tokens_used: number | null;
  triage_completed_at: string | null;
  deep_analysis_result: Record<string, unknown> | null;
  deep_analysis_model: string | null;
  deep_analysis_tokens_used: number | null;
  deep_analysis_completed_at: string | null;
  synthesis_result: Record<string, unknown> | null;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  summary: string | null;
  error_message: string | null;
  total_cost_usd: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  package_name: string | null;
  package_registry: string | null;
  version_string: string | null;
  previous_version_string: string | null;
  finding_count: number;
}

export interface Finding {
  id: string;
  analysis_id: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  evidence: { items?: Evidence[] } | null;
  confidence: number;
  mitre_technique: string | null;
  remediation: string | null;
  false_positive: boolean;
  created_at: string;
}

export interface Evidence {
  file_path: string;
  line_start: number;
  line_end: number;
  snippet: string;
  explanation: string;
}

export interface FeedItem {
  id: string;
  type: string;
  package_name: string;
  package_registry: string;
  version_string: string;
  risk_level: RiskLevel | null;
  risk_score: number | null;
  summary: string | null;
  finding_count: number;
  created_at: string;
}

export interface Stats {
  total_packages: number;
  total_analyses: number;
  analyses_today: number;
  flagged_count: number;
  critical_count: number;
  avg_risk_score: number | null;
  total_findings: number;
  total_vulnerability_scans: number;
  total_vulnerabilities: number;
  critical_vulnerabilities: number;
}

export interface VulnerabilityScan {
  id: string;
  package_id: string;
  version_string: string;
  status: string;
  trigger: string;
  source_size_bytes: number | null;
  source_file_count: number | null;
  total_cost_usd: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  package_name: string | null;
  package_registry: string | null;
  vulnerability_count: number;
}

export interface Vulnerability {
  id: string;
  scan_id: string;
  package_id: string;
  category: string;
  subcategory: string | null;
  severity: string;
  title: string;
  description: string;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  code_snippet: string | null;
  poc_code: string | null;
  poc_description: string | null;
  attack_vector: string | null;
  impact: string | null;
  cvss_score: number | null;
  cwe_id: string | null;
  attack_chain: string | null;
  confidence: number;
  validated: boolean;
  false_positive: boolean;
  remediation: string | null;
  created_at: string;
  package_name: string | null;
  package_registry: string | null;
  version_string: string | null;
}

export interface PuzzleOption {
  text: string;
  index: number;
  is_correct?: boolean;  // Only in results
}

export interface Puzzle {
  id: string;
  vulnerability_id: string;
  challenge_type: string;
  title: string;
  scenario: string;
  options: PuzzleOption[];
  difficulty: number;
  created_at: string;
  vote_count: number;
  package_name: string | null;
  package_registry: string | null;
  vuln_title: string | null;
}

export interface PuzzleResult {
  id: string;
  title: string;
  scenario: string;
  options: { text: string; is_correct: boolean }[];
  explanation: string;
  consensus: Record<number, number>;
  total_votes: number;
  user_was_correct: boolean;
}

export interface AlertConfig {
  id: string;
  name: string;
  channel_type: "slack" | "webhook" | "email";
  channel_config: Record<string, unknown>;
  min_risk_level: string;
  registries: string[] | null;
  packages: string[] | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}
