"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { StudioNav } from "@/components/studio-nav";
import { ApiError, apiFetch, getApiUrl } from "@/lib/api";
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
  const [metaError, setMetaError] = useState<string | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);

  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [orgBusy, setOrgBusy] = useState(false);
  const [orgMessage, setOrgMessage] = useState<{
    tone: "ok" | "error";
    text: string;
  } | null>(null);
  const [createdOrg, setCreatedOrg] = useState<Organization | null>(null);

  const [organizationId, setOrganizationId] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [projectBusy, setProjectBusy] = useState(false);
  const [projectMessage, setProjectMessage] = useState<{
    tone: "ok" | "error";
    text: string;
  } | null>(null);

  const [projects, setProjects] = useState<Project[]>([]);
  const [listBusy, setListBusy] = useState(false);
  const [listMessage, setListMessage] = useState<{
    tone: "ok" | "error" | "warn";
    text: string;
  } | null>(null);

  const loadMeta = useCallback(async () => {
    setMetaLoading(true);
    setMetaError(null);
    try {
      const data = await apiFetch<PlatformMeta>("/api/v1/meta");
      setMeta(data);
    } catch (err) {
      setMeta(null);
      setMetaError(
        err instanceof ApiError
          ? err.message
          : "Failed to load platform metadata.",
      );
    } finally {
      setMetaLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMeta();
  }, [loadMeta]);

  async function onCreateOrg(event: FormEvent) {
    event.preventDefault();
    setOrgBusy(true);
    setOrgMessage(null);
    try {
      const org = await apiFetch<Organization>("/api/v1/organizations", {
        method: "POST",
        body: JSON.stringify({
          name: orgName.trim(),
          slug: (orgSlug || slugify(orgName)).trim(),
        }),
      });
      const workspace = await apiFetch<Workspace>("/api/v1/workspaces", {
        method: "POST",
        body: JSON.stringify({
          organization_id: org.id,
          name: "Main",
          slug: "main",
        }),
      });
      setCreatedOrg(org);
      setOrganizationId(org.id);
      setWorkspaceId(workspace.id);
      setOrgMessage({
        tone: "ok",
        text: `Created organization “${org.name}” and workspace “${workspace.name}”.`,
      });
    } catch (err) {
      setOrgMessage({
        tone: "error",
        text:
          err instanceof ApiError
            ? err.message
            : "Failed to create organization.",
      });
    } finally {
      setOrgBusy(false);
    }
  }

  async function onCreateProject(event: FormEvent) {
    event.preventDefault();
    setProjectBusy(true);
    setProjectMessage(null);
    try {
      const project = await apiFetch<Project>("/api/v1/projects", {
        method: "POST",
        body: JSON.stringify({
          organization_id: organizationId.trim(),
          workspace_id: workspaceId.trim(),
          name: projectName.trim(),
          description: projectDescription.trim(),
        }),
      });
      setProjectMessage({
        tone: "ok",
        text: `Created project “${project.name}” (${project.id}).`,
      });
      setProjectName("");
      setProjectDescription("");
      if (organizationId && workspaceId) {
        void loadProjects();
      }
    } catch (err) {
      setProjectMessage({
        tone: "error",
        text:
          err instanceof ApiError ? err.message : "Failed to create project.",
      });
    } finally {
      setProjectBusy(false);
    }
  }

  async function loadProjects() {
    if (!organizationId.trim() || !workspaceId.trim()) {
      setListMessage({
        tone: "warn",
        text: "Provide organization_id and workspace_id to list projects.",
      });
      return;
    }
    setListBusy(true);
    setListMessage(null);
    try {
      const data = await apiFetch<{ items: Project[] }>(
        `/api/v1/workspaces/${encodeURIComponent(organizationId.trim())}/${encodeURIComponent(workspaceId.trim())}/projects`,
      );
      const list = data.items ?? [];
      setProjects(list);
      setListMessage({
        tone: "ok",
        text:
          list.length === 0
            ? "No projects yet for this org/workspace."
            : `Loaded ${list.length} project(s).`,
      });
    } catch (err) {
      setProjects([]);
      setListMessage({
        tone: "error",
        text:
          err instanceof ApiError ? err.message : "Failed to list projects.",
      });
    } finally {
      setListBusy(false);
    }
  }

  return (
    <>
      <StudioNav active="workspace" />
      <main className="studio-main">
        <h1>Workspace studio</h1>
        <p className="lede">
          Talk to the Formal Platform API at{" "}
          <code>{getApiUrl()}</code>. Create an organization, then a project
          under a workspace.
        </p>

        <section className="panel" aria-labelledby="meta-heading">
          <h2 id="meta-heading">Platform meta</h2>
          {metaLoading && <p className="note">Loading /api/v1/meta…</p>}
          {metaError && (
            <p className="status status--error" role="alert">
              {metaError}
            </p>
          )}
          {meta && (
            <div className="panel-meta">
              <dl className="meta-row">
                <dt>Phase</dt>
                <dd>{meta.phase}</dd>
              </dl>
              <dl className="meta-row">
                <dt>API</dt>
                <dd>{meta.api_version}</dd>
              </dl>
              <dl className="meta-row">
                <dt>Certificate schema</dt>
                <dd>{meta.certificate_schema_version}</dd>
              </dl>
              <dl className="meta-row">
                <dt>Problem schema</dt>
                <dd>{meta.problem_spec_schema_version}</dd>
              </dl>
              {meta.proof_service_url && (
                <dl className="meta-row">
                  <dt>Proof service</dt>
                  <dd>{meta.proof_service_url}</dd>
                </dl>
              )}
              <ul className="feature-list">
                {Object.entries(meta.features ?? {}).map(([key, on]) => (
                  <li key={key} className={on ? "on" : "off"}>
                    {key}
                    {on ? "" : " · off"}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="form-actions" style={{ marginTop: "0.9rem" }}>
            <button
              type="button"
              className="btn"
              onClick={() => void loadMeta()}
              disabled={metaLoading}
            >
              Refresh meta
            </button>
          </div>
        </section>

        <section className="panel" aria-labelledby="org-heading">
          <h2 id="org-heading">Create organization</h2>
          <form className="form-grid" onSubmit={onCreateOrg}>
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
                {orgBusy ? "Creating…" : "Create org"}
              </button>
            </div>
          </form>
          {orgMessage && (
            <p className={`status status--${orgMessage.tone}`} role="status">
              {orgMessage.text}
            </p>
          )}
          {createdOrg && (
            <p className="note" style={{ marginTop: "0.85rem", marginBottom: 0 }}>
              Tip: projects also need a <code>workspace_id</code> from{" "}
              <code>POST /api/v1/workspaces</code> (or your seeded workspace).
            </p>
          )}
        </section>

        <section className="panel" aria-labelledby="project-heading">
          <h2 id="project-heading">Create project</h2>
          <form className="form-grid" onSubmit={onCreateProject}>
            <label>
              Organization ID
              <input
                required
                value={organizationId}
                onChange={(e) => setOrganizationId(e.target.value)}
                placeholder="org uuid"
              />
            </label>
            <label>
              Workspace ID
              <input
                required
                value={workspaceId}
                onChange={(e) => setWorkspaceId(e.target.value)}
                placeholder="workspace uuid"
              />
            </label>
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
                rows={3}
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
                onClick={() => void loadProjects()}
                disabled={listBusy}
              >
                {listBusy ? "Loading…" : "List projects"}
              </button>
            </div>
          </form>
          {projectMessage && (
            <p
              className={`status status--${projectMessage.tone}`}
              role="status"
            >
              {projectMessage.text}
            </p>
          )}
          {listMessage && (
            <p className={`status status--${listMessage.tone}`} role="status">
              {listMessage.text}
            </p>
          )}
          {projects.length > 0 && (
            <ul className="project-list" style={{ marginTop: "0.9rem" }}>
              {projects.map((p) => (
                <li key={p.id}>
                  <span className="name">{p.name}</span>
                  <span className="meta">
                    {p.id}
                    {p.status ? ` · ${p.status}` : ""}
                    {p.description ? ` — ${p.description}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
