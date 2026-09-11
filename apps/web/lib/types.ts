export type PlatformMeta = {
  api_version: string;
  certificate_schema_version: string;
  problem_spec_schema_version: string;
  phase: string;
  proof_service_url?: string;
  features: Record<string, boolean>;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  created_at?: string;
};

export type Workspace = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  created_at?: string;
};

export type Project = {
  id: string;
  organization_id: string;
  workspace_id: string;
  name: string;
  description?: string;
  status?: string;
  created_at?: string;
};

export type IssuedCertificate = {
  certificate_id: string;
  root_hash: string;
  lean_verified: boolean;
  status?: string;
  claim_statement?: string;
  theorem_name?: string;
  organization_id?: string;
  workspace_id?: string;
  project_id?: string | null;
  run_id?: string | null;
  source?: string;
  issued_by?: string;
  created_at?: string | null;
  bundle_content_hash?: string;
  certificate?: Record<string, unknown>;
  verification?: Record<string, unknown>;
};

export type DemoCertificateIssue = IssuedCertificate;


export type AgentRunSummary = {
  run_id: string;
  graph: string;
  status: string;
  pending_human_review?: boolean;
  updated_at?: string | null;
  created_at?: string | null;
};

export type AgentRun = {
  run_id: string;
  organization_id: string;
  workspace_id: string;
  project_id: string;
  graph:
    | "problem_modelling"
    | "formalization"
    | "proof"
    | "certification"
    | string;
  status: string;
  problem_text?: string;
  entities: Record<string, unknown>[];
  assumptions: Record<string, unknown>[];
  goals: Record<string, unknown>[];
  claims: Record<string, unknown>[];
  lean_skeleton?: string | null;
  candidate_proof?: Record<string, unknown> | null;
  lean_project_path?: string | null;
  verification_report?: Record<string, unknown> | null;
  lean_verified?: boolean;
  certificate_ready?: boolean;
  certificate_id?: string | null;
  issued_certificate?: IssuedCertificate | null;
  pending_human_review?: boolean;
  interrupt_node?: string | null;
  history: string[];
  error?: string | null;
};
