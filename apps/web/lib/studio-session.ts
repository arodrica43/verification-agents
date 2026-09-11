import type { Organization, Workspace } from "@/lib/types";

const STORAGE_KEY = "formal.studio.session.v1";
const CERT_HISTORY_KEY = "formal.studio.cert-history.v1";

export type StudioSession = {
  organizationId: string | null;
  workspaceId: string | null;
};

export type CertHistoryItem = {
  certificate_id: string;
  root_hash: string;
  lean_verified: boolean;
  issued_at: string;
  claim?: string;
  theorem?: string;
};

export function loadStudioSession(): StudioSession {
  if (typeof window === "undefined") {
    return { organizationId: null, workspaceId: null };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { organizationId: null, workspaceId: null };
    const parsed = JSON.parse(raw) as StudioSession;
    return {
      organizationId: parsed.organizationId ?? null,
      workspaceId: parsed.workspaceId ?? null,
    };
  } catch {
    return { organizationId: null, workspaceId: null };
  }
}

export function saveStudioSession(session: StudioSession): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearStudioSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function loadCertHistory(): CertHistoryItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(CERT_HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as CertHistoryItem[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function pushCertHistory(item: CertHistoryItem): CertHistoryItem[] {
  const next = [item, ...loadCertHistory().filter((c) => c.certificate_id !== item.certificate_id)].slice(
    0,
    25,
  );
  if (typeof window !== "undefined") {
    window.localStorage.setItem(CERT_HISTORY_KEY, JSON.stringify(next));
  }
  return next;
}

export function pickDefaultWorkspace(
  workspaces: Workspace[],
  preferredId: string | null,
): Workspace | null {
  if (!workspaces.length) return null;
  if (preferredId) {
    const match = workspaces.find((w) => w.id === preferredId);
    if (match) return match;
  }
  return workspaces.find((w) => w.slug === "main") ?? workspaces[0];
}

export function pickDefaultOrg(
  orgs: Organization[],
  preferredId: string | null,
): Organization | null {
  if (!orgs.length) return null;
  if (preferredId) {
    const match = orgs.find((o) => o.id === preferredId);
    if (match) return match;
  }
  return orgs[0];
}
