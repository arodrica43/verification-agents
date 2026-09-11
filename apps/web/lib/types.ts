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

export type DemoCertificateIssue = {
  certificate_id?: string;
  root_hash?: string;
  lean_verified?: boolean;
  certificate?: Record<string, unknown>;
  verification?: Record<string, unknown>;
};
