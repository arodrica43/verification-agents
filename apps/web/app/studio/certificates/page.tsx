"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { StudioNav } from "@/components/studio-nav";
import { ApiError, apiDownload, apiFetch } from "@/lib/api";
import { loadStudioSession } from "@/lib/studio-session";
import type { IssuedCertificate, Organization, Workspace } from "@/lib/types";

export default function CertificatesPage() {
  const [busy, setBusy] = useState(false);
  const [requireLean, setRequireLean] = useState(true);
  const [items, setItems] = useState<IssuedCertificate[]>([]);
  const [selected, setSelected] = useState<IssuedCertificate | null>(null);
  const [message, setMessage] = useState<{
    tone: "ok" | "error" | "warn";
    text: string;
  } | null>(null);
  const [contextLabel, setContextLabel] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);

  const refresh = useCallback(async (orgId: string) => {
    const data = await apiFetch<{ items: IssuedCertificate[] }>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/certificates`,
    );
    setItems(data.items ?? []);
  }, []);

  useEffect(() => {
    const session = loadStudioSession();
    const envLean =
      (process.env.NEXT_PUBLIC_REQUIRE_LEAN ?? "true").toLowerCase() === "true";
    setRequireLean(envLean);

    (async () => {
      try {
        const orgs = await apiFetch<{ items: Organization[] }>(
          "/api/v1/organizations",
        );
        const orgList = orgs.items ?? [];
        const orgId =
          session.organizationId &&
          orgList.some((o) => o.id === session.organizationId)
            ? session.organizationId
            : orgList[0]?.id ?? null;
        if (!orgId) {
          setBootError("Create an organization in Studio before issuing certificates.");
          return;
        }
        setOrganizationId(orgId);
        const workspaces = await apiFetch<{ items: Workspace[] }>(
          `/api/v1/organizations/${encodeURIComponent(orgId)}/workspaces`,
        );
        const wsList = workspaces.items ?? [];
        const wsId =
          session.workspaceId && wsList.some((w) => w.id === session.workspaceId)
            ? session.workspaceId
            : wsList[0]?.id ?? null;
        setWorkspaceId(wsId);
        const org = orgList.find((o) => o.id === orgId);
        const ws = wsList.find((w) => w.id === wsId);
        if (org) setContextLabel(ws ? `${org.name} / ${ws.name}` : org.name);
        await refresh(orgId);
      } catch (err) {
        setBootError(
          err instanceof ApiError ? err.message : "Failed to load certificates.",
        );
      }
    })();
  }, [refresh]);

  async function issueDemo() {
    if (!organizationId || !workspaceId) {
      setMessage({
        tone: "error",
        text: "Select an organization and workspace in Studio first.",
      });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const data = await apiFetch<IssuedCertificate>(
        "/api/v1/certificates/demo/issue",
        {
          method: "POST",
          body: JSON.stringify({
            organization_id: organizationId,
            workspace_id: workspaceId,
            allow_unverified: !requireLean,
            require_lean: requireLean,
          }),
          timeoutMs: 120_000,
        },
      );
      setSelected(data);
      await refresh(organizationId);
      setMessage({
        tone: "ok",
        text: data.lean_verified
          ? `Certificate ${data.certificate_id} issued with Lean verification.`
          : `Certificate ${data.certificate_id} issued (Lean not required for this demo).`,
      });
    } catch (err) {
      setMessage({
        tone: "error",
        text:
          err instanceof ApiError
            ? err.message
            : "Failed to issue demo certificate.",
      });
    } finally {
      setBusy(false);
    }
  }

  async function downloadBundle(cert: IssuedCertificate) {
    try {
      await apiDownload(
        `/api/v1/certificates/${encodeURIComponent(cert.certificate_id)}/bundle`,
        `certificate-${cert.certificate_id}.zip`,
      );
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Download failed.",
      });
    }
  }

  return (
    <>
      <StudioNav active="certificates" contextLabel={contextLabel} />
      <main className="studio-main">
        <h1>Certificates</h1>
        <p className="lede">
          Issued certificates are stored on the Formal Platform (not only in this
          browser). Open a project, verify with Lean, then issue — or use the
          agent-policy demo below.
        </p>
        {bootError && (
          <p className="status status--error" role="alert">
            {bootError}
          </p>
        )}

        <section className="panel" aria-labelledby="issue-heading">
          <h2 id="issue-heading">Issue demo certificate</h2>
          <p className="note">
            Uses the built-in agent-policy Lean project. Prefer project-scoped
            issuance after <strong>Verify with Lean</strong> for your own systems.
          </p>
          <label className="check-row">
            <input
              type="checkbox"
              checked={requireLean}
              onChange={(e) => setRequireLean(e.target.checked)}
            />
            Require Lean verification (needs lake on the API host)
          </label>
          <div className="form-actions">
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy || !organizationId}
              onClick={() => void issueDemo()}
            >
              Issue demo certificate
            </button>
            <Link className="btn" href="/studio">
              Open studio workspace
            </Link>
          </div>
          {message && (
            <p className={`status status--${message.tone}`} role="status">
              {message.text}
            </p>
          )}
        </section>

        <section className="panel" aria-labelledby="list-heading">
          <h2 id="list-heading">Issued certificates</h2>
          {items.length === 0 ? (
            <p className="note empty-hint">
              No certificates issued yet for this organization.
            </p>
          ) : (
            <ul className="project-list">
              {items.map((c) => (
                <li key={c.certificate_id}>
                  <button
                    type="button"
                    className="name linkish"
                    onClick={() => setSelected(c)}
                  >
                    {c.theorem_name || c.certificate_id}
                  </button>
                  <span className="meta">
                    {c.lean_verified ? "lean_verified" : "unverified"} ·{" "}
                    {c.source ?? "issued"} · {c.created_at ?? ""}
                  </span>
                  <span className="meta">{c.claim_statement}</span>
                  <div className="form-actions">
                    <button
                      type="button"
                      className="btn"
                      onClick={() => void downloadBundle(c)}
                    >
                      Download bundle
                    </button>
                    {c.project_id ? (
                      <Link
                        className="btn"
                        href={`/studio/projects/${c.project_id}`}
                      >
                        Open project
                      </Link>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {selected && (
          <section className="panel" aria-labelledby="detail-heading">
            <h2 id="detail-heading">Certificate detail</h2>
            <p className="note">
              id={selected.certificate_id} · root={selected.root_hash} · lean=
              {String(selected.lean_verified)}
            </p>
            <pre className="code-block">
              {JSON.stringify(
                {
                  certificate_id: selected.certificate_id,
                  root_hash: selected.root_hash,
                  lean_verified: selected.lean_verified,
                  claim_statement: selected.claim_statement,
                  theorem_name: selected.theorem_name,
                  verification: selected.verification,
                  certificate: selected.certificate,
                },
                null,
                2,
              )}
            </pre>
          </section>
        )}
      </main>
    </>
  );
}
