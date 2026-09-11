"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { StudioNav } from "@/components/studio-nav";
import { ApiError, apiFetch } from "@/lib/api";
import {
  loadStudioSession,
  pickDefaultOrg,
  pickDefaultWorkspace,
  saveStudioSession,
} from "@/lib/studio-session";
import type { Organization, PlatformMeta, Project, Workspace } from "@/lib/types";

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export default function StudioPage() {
  const [meta, setMeta] = useState<PlatformMeta | null>(null);
  const [principalId, setPrincipalId] = useState<string | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);

  const [organizationId, setOrganizationId] = useState<string>("");
  const [workspaceId, setWorkspaceId] = useState<string>("");

  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [orgBusy, setOrgBusy] = useState(false);
  const [orgMessage, setOrgMessage] = useState<string | null>(null);

  const [wsName, setWsName] = useState("");
  const [wsSlug, setWsSlug] = useState("");
  const [wsBusy, setWsBusy] = useState(false);
  const [wsMessage, setWsMessage] = useState<string | null>(null);

  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [projectBusy, setProjectBusy] = useState(false);
  const [projectMessage, setProjectMessage] = useState<string | null>(null);
  const [listMessage, setListMessage] = useState<string | null>(null);

  const selectedOrg = useMemo(
    () => orgs.find((o) => o.id === organizationId) ?? null,
    [orgs, organizationId],
  );
  const selectedWorkspace = useMemo(
    () => workspaces.find((w) => w.id === workspaceId) ?? null,
    [workspaces, workspaceId],
  );

  const persistSelection = useCallback((orgId: string | null, wsId: string | null) => {
    saveStudioSession({ organizationId: orgId, workspaceId: wsId });
  }, []);

  const loadProjects = useCallback(
    async (orgId: string, wsId: string) => {
      if (!orgId || !wsId) {
        setProjects([]);
        return;
      }
      try {
        const data = await apiFetch<{ items: Project[] }>(
          `/api/v1/workspaces/${encodeURIComponent(orgId)}/${encodeURIComponent(wsId)}/projects`,
        );
        setProjects(data.items ?? []);
        setListMessage(null);
      } catch (err) {
        setProjects([]);
        setListMessage(
          err instanceof ApiError ? err.message : "Failed to list projects.",
        );
      }
    },
    [],
  );

  const loadWorkspaces = useCallback(
    async (orgId: string, preferredWsId: string | null) => {
      if (!orgId) {
        setWorkspaces([]);
        setWorkspaceId("");
        return;
      }
      const data = await apiFetch<{ items: Workspace[] }>(
        `/api/v1/organizations/${encodeURIComponent(orgId)}/workspaces`,
      );
      const items = data.items ?? [];
      setWorkspaces(items);
      const picked = pickDefaultWorkspace(items, preferredWsId);
      const nextWsId = picked?.id ?? "";
      setWorkspaceId(nextWsId);
      persistSelection(orgId, nextWsId || null);
      if (nextWsId) {
        await loadProjects(orgId, nextWsId);
      } else {
        setProjects([]);
      }
    },
    [loadProjects, persistSelection],
  );

  const refreshOrgs = useCallback(
    async (preferredOrgId: string | null, preferredWsId: string | null) => {
      const data = await apiFetch<{ items: Organization[] }>("/api/v1/organizations");
      const items = data.items ?? [];
      setOrgs(items);
      const picked = pickDefaultOrg(items, preferredOrgId);
      const nextOrgId = picked?.id ?? "";
      setOrganizationId(nextOrgId);
      if (nextOrgId) {
        await loadWorkspaces(nextOrgId, preferredWsId);
      } else {
        setWorkspaces([]);
        setWorkspaceId("");
        setProjects([]);
        persistSelection(null, null);
      }
    },
    [loadWorkspaces, persistSelection],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setBooting(true);
      setBootError(null);
      try {
        const session = loadStudioSession();
        const [metaData, me] = await Promise.all([
          apiFetch<PlatformMeta>("/api/v1/meta"),
          apiFetch<{ principal_id: string }>("/api/v1/me"),
        ]);
        if (cancelled) return;
        setMeta(metaData);
        setPrincipalId(me.principal_id);
        await refreshOrgs(session.organizationId, session.workspaceId);
      } catch (err) {
        if (!cancelled) {
          setBootError(
            err instanceof ApiError
              ? err.message
              : "Could not load studio. Is the API running?",
          );
        }
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshOrgs]);

  async function onSelectOrg(nextOrgId: string) {
    setOrganizationId(nextOrgId);
    setOrgMessage(null);
    setWsMessage(null);
    setProjectMessage(null);
    try {
      await loadWorkspaces(nextOrgId, null);
    } catch (err) {
      setBootError(
        err instanceof ApiError ? err.message : "Failed to load workspaces.",
      );
    }
  }

  async function onSelectWorkspace(nextWsId: string) {
    setWorkspaceId(nextWsId);
    persistSelection(organizationId || null, nextWsId || null);
    if (organizationId && nextWsId) {
      await loadProjects(organizationId, nextWsId);
    }
  }

  async function onCreateOrg(event: FormEvent) {
    event.preventDefault();
    setOrgBusy(true);
    setOrgMessage(null);
    try {
      const org = await apiFetch<Organization & { default_workspace?: Workspace }>(
        "/api/v1/organizations",
        {
          method: "POST",
          body: JSON.stringify({
            name: orgName.trim(),
            slug: (orgSlug || slugify(orgName)).trim(),
          }),
        },
      );
      setOrgName("");
      setOrgSlug("");
      setOrgMessage(`Created “${org.name}”.`);
      await refreshOrgs(org.id, org.default_workspace?.id ?? null);
    } catch (err) {
      setOrgMessage(
        err instanceof ApiError ? err.message : "Failed to create organization.",
      );
    } finally {
      setOrgBusy(false);
    }
  }

  async function onCreateWorkspace(event: FormEvent) {
    event.preventDefault();
    if (!organizationId) return;
    setWsBusy(true);
    setWsMessage(null);
    try {
      const ws = await apiFetch<Workspace>("/api/v1/workspaces", {
        method: "POST",
        body: JSON.stringify({
          organization_id: organizationId,
          name: wsName.trim(),
          slug: (wsSlug || slugify(wsName)).trim(),
        }),
      });
      setWsName("");
      setWsSlug("");
      setWsMessage(`Created workspace “${ws.name}”.`);
      await loadWorkspaces(organizationId, ws.id);
    } catch (err) {
      setWsMessage(
        err instanceof ApiError ? err.message : "Failed to create workspace.",
      );
    } finally {
      setWsBusy(false);
    }
  }

  async function onCreateProject(event: FormEvent) {
    event.preventDefault();
    if (!organizationId || !workspaceId) return;
    setProjectBusy(true);
    setProjectMessage(null);
    try {
      const project = await apiFetch<Project>("/api/v1/projects", {
        method: "POST",
        body: JSON.stringify({
          organization_id: organizationId,
          workspace_id: workspaceId,
          name: projectName.trim(),
          description: projectDescription.trim(),
        }),
      });
      setProjectName("");
      setProjectDescription("");
      setProjectMessage(`Created “${project.name}”.`);
      await loadProjects(organizationId, workspaceId);
    } catch (err) {
      setProjectMessage(
        err instanceof ApiError ? err.message : "Failed to create project.",
      );
    } finally {
      setProjectBusy(false);
    }
  }

  return (
    <>
      <StudioNav
        active="workspace"
        contextLabel={
          selectedOrg
            ? `${selectedOrg.name}${selectedWorkspace ? ` / ${selectedWorkspace.name}` : ""}`
            : null
        }
      />
      <main className="studio-main">
        <h1>Workspace</h1>
        <p className="lede">
          Create and switch organizations by name. Your selection is remembered
          in this browser — no UUID pasting.
        </p>

        {booting && <p className="note">Loading your organizations…</p>}
        {bootError && (
          <p className="status status--error" role="alert">
            {bootError}
          </p>
        )}

        {!booting && !bootError && (
          <>
            <section className="panel context-panel" aria-labelledby="context-heading">
              <h2 id="context-heading">Current context</h2>
              <p className="note" style={{ marginTop: 0 }}>
                Signed in as <code>{principalId ?? "—"}</code>
                {meta ? (
                  <>
                    {" "}
                    · API <code>{meta.api_version}</code> · phase{" "}
                    <code>{meta.phase}</code>
                  </>
                ) : null}
              </p>
              <div className="form-grid form-grid--2">
                <label>
                  Organization
                  <select
                    value={organizationId}
                    onChange={(e) => void onSelectOrg(e.target.value)}
                    disabled={orgs.length === 0}
                  >
                    {orgs.length === 0 ? (
                      <option value="">No organizations yet</option>
                    ) : (
                      orgs.map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.name} ({o.slug})
                        </option>
                      ))
                    )}
                  </select>
                </label>
                <label>
                  Workspace
                  <select
                    value={workspaceId}
                    onChange={(e) => void onSelectWorkspace(e.target.value)}
                    disabled={!organizationId || workspaces.length === 0}
                  >
                    {workspaces.length === 0 ? (
                      <option value="">No workspaces</option>
                    ) : (
                      workspaces.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.name} ({w.slug})
                        </option>
                      ))
                    )}
                  </select>
                </label>
              </div>
              <div className="form-actions">
                <button
                  type="button"
                  className="btn"
                  onClick={() =>
                    void refreshOrgs(organizationId || null, workspaceId || null)
                  }
                >
                  Refresh
                </button>
              </div>
            </section>

            <section className="panel" aria-labelledby="org-heading">
              <h2 id="org-heading">New organization</h2>
              <form className="form-grid form-grid--2" onSubmit={onCreateOrg}>
                <label>
                  Name
                  <input
                    required
                    value={orgName}
                    onChange={(e) => {
                      setOrgName(e.target.value);
                      if (!orgSlug || orgSlug === slugify(orgName)) {
                        setOrgSlug(slugify(e.target.value));
                      }
                    }}
                    placeholder="Acme Research"
                  />
                </label>
                <label>
                  Slug
                  <input
                    required
                    value={orgSlug}
                    onChange={(e) => setOrgSlug(e.target.value)}
                    placeholder="acme-research"
                    pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                  />
                </label>
                <div className="form-actions">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={orgBusy || !orgName.trim()}
                  >
                    {orgBusy ? "Creating…" : "Create organization"}
                  </button>
                </div>
              </form>
              {orgMessage && (
                <p className="status status--ok" role="status">
                  {orgMessage}
                </p>
              )}
            </section>

            <section className="panel" aria-labelledby="ws-heading">
              <h2 id="ws-heading">New workspace</h2>
              {!organizationId ? (
                <p className="note" style={{ marginBottom: 0 }}>
                  Select or create an organization first.
                </p>
              ) : (
                <form className="form-grid form-grid--2" onSubmit={onCreateWorkspace}>
                  <label>
                    Name
                    <input
                      required
                      value={wsName}
                      onChange={(e) => {
                        setWsName(e.target.value);
                        if (!wsSlug || wsSlug === slugify(wsName)) {
                          setWsSlug(slugify(e.target.value));
                        }
                      }}
                      placeholder="Experiments"
                    />
                  </label>
                  <label>
                    Slug
                    <input
                      required
                      value={wsSlug}
                      onChange={(e) => setWsSlug(e.target.value)}
                      placeholder="experiments"
                      pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                    />
                  </label>
                  <div className="form-actions">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={wsBusy || !wsName.trim()}
                    >
                      {wsBusy ? "Creating…" : "Create workspace"}
                    </button>
                  </div>
                </form>
              )}
              {wsMessage && (
                <p className="status status--ok" role="status">
                  {wsMessage}
                </p>
              )}
            </section>

            <section className="panel" aria-labelledby="project-heading">
              <h2 id="project-heading">Projects</h2>
              {!workspaceId ? (
                <p className="note">Select a workspace to manage projects.</p>
              ) : (
                <>
                  <form className="form-grid" onSubmit={onCreateProject}>
                    <label>
                      Project name
                      <input
                        required
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                        placeholder="Agent policy demo"
                      />
                    </label>
                    <label>
                      Description
                      <textarea
                        rows={2}
                        value={projectDescription}
                        onChange={(e) => setProjectDescription(e.target.value)}
                        placeholder="Optional"
                      />
                    </label>
                    <div className="form-actions">
                      <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={projectBusy || !projectName.trim()}
                      >
                        {projectBusy ? "Creating…" : "Create project"}
                      </button>
                      <button
                        type="button"
                        className="btn"
                        onClick={() =>
                          void loadProjects(organizationId, workspaceId)
                        }
                      >
                        Reload list
                      </button>
                    </div>
                  </form>
                  {projectMessage && (
                    <p className="status status--ok" role="status">
                      {projectMessage}
                    </p>
                  )}
                  {listMessage && (
                    <p className="status status--error" role="alert">
                      {listMessage}
                    </p>
                  )}
                  {projects.length === 0 ? (
                    <p className="note empty-hint">
                      No projects in this workspace yet.
                    </p>
                  ) : (
                    <ul className="project-list">
                      {projects.map((p) => (
                        <li key={p.id}>
                          <Link className="name" href={`/studio/projects/${p.id}`}>
                            {p.name}
                          </Link>
                          <span className="meta">
                            {p.status ? `${p.status}` : "active"}
                            {p.description ? ` — ${p.description}` : ""}
                            {" · "}
                            <Link href={`/studio/projects/${p.id}`}>Open →</Link>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </section>
          </>
        )}
      </main>
    </>
  );
}
