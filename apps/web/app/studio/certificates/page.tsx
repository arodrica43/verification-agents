"use client";

import { useEffect, useState } from "react";
import { StudioNav } from "@/components/studio-nav";
import { ApiError, apiFetch } from "@/lib/api";
import {
  CertHistoryItem,
  loadCertHistory,
  loadStudioSession,
  pushCertHistory,
} from "@/lib/studio-session";
import type { DemoCertificateIssue, Organization, Workspace } from "@/lib/types";

export default function CertificatesPage() {
  const [busy, setBusy] = useState(false);
  const [requireLean, setRequireLean] = useState(false);
  const [result, setResult] = useState<DemoCertificateIssue | null>(null);
  const [history, setHistory] = useState<CertHistoryItem[]>([]);
  const [message, setMessage] = useState<{
    tone: "ok" | "error" | "warn";
    text: string;
  } | null>(null);
  const [contextLabel, setContextLabel] = useState<string | null>(null);

  useEffect(() => {
    setHistory(loadCertHistory());
    const envLean =
      (process.env.NEXT_PUBLIC_REQUIRE_LEAN ?? "false").toLowerCase() === "true";
    setRequireLean(envLean);

    const session = loadStudioSession();
    if (!session.organizationId) return;
    (async () => {
      try {
        const [orgs, workspaces] = await Promise.all([
          apiFetch<{ items: Organization[] }>("/api/v1/organizations"),
          apiFetch<{ items: Workspace[] }>(
            `/api/v1/organizations/${encodeURIComponent(session.organizationId!)}/workspaces`,
          ),
        ]);
        const org = (orgs.items ?? []).find((o) => o.id === session.organizationId);
        const ws = (workspaces.items ?? []).find((w) => w.id === session.workspaceId);
        if (org) {
          setContextLabel(ws ? `${org.name} / ${ws.name}` : org.name);
        }
      } catch {
        /* context label is optional */
      }
    })();
  }, []);

  async function issueDemo() {
    setBusy(true);
    setMessage(null);
    try {
      const data = await apiFetch<DemoCertificateIssue>(
        "/api/v1/certificates/demo/issue",
        {
          method: "POST",
          body: JSON.stringify({
            allow_unverified: !requireLean,
            require_lean: requireLean,
          }),
        },
      );
      setResult(data);
      const certificate = data.certificate;
      const claim =
        certificate &&
        typeof certificate.claim === "object" &&
        certificate.claim !== null
          ? (certificate.claim as { statement?: string }).statement
          : undefined;
      const theorem =
        certificate &&
        typeof certificate.formal_theorem === "object" &&
        certificate.formal_theorem !== null &&
        "name" in certificate.formal_theorem
          ? String((certificate.formal_theorem as { name?: string }).name)
          : undefined;

      if (data.certificate_id && data.root_hash) {
        setHistory(
          pushCertHistory({
            certificate_id: data.certificate_id,
            root_hash: data.root_hash,
            lean_verified: Boolean(data.lean_verified),
            issued_at: new Date().toISOString(),
            claim,
            theorem,
          }),
        );
      }

      setMessage({
        tone: "ok",
        text: data.lean_verified
          ? "Demo certificate issued with Lean verification."
          : "Demo certificate issued without Lean (local demo mode).",
      });
    } catch (err) {
      setResult(null);
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

  function downloadJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.certificate_id ?? "certificate"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const certificate = result?.certificate;
  const claim =
    certificate &&
    typeof certificate.claim === "object" &&
    certificate.claim !== null
      ? (certificate.claim as { statement?: string })
      : null;

  return (
    <>
      <StudioNav active="certificates" contextLabel={contextLabel} />
      <main className="studio-main">
        <h1>Certificates</h1>
        <p className="lede">
          Issue the agent-policy demo certificate and keep a local history of
          what you issued in this browser.
        </p>

        <section className="panel" aria-labelledby="issue-heading">
          <h2 id="issue-heading">Issue demo certificate</h2>
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
              onClick={() => void issueDemo()}
              disabled={busy}
            >
              {busy ? "Issuing…" : "Issue demo certificate"}
            </button>
            {result && (
              <button type="button" className="btn" onClick={downloadJson}>
                Download JSON
              </button>
            )}
          </div>
          {message && (
            <p className={`status status--${message.tone}`} role="status">
              {message.text}
            </p>
          )}
        </section>

        {result && (
          <section className="panel" aria-labelledby="result-heading">
            <h2 id="result-heading">Latest issue</h2>
            <dl className="cert-summary">
              <div>
                <dt>Certificate ID</dt>
                <dd>{result.certificate_id ?? "—"}</dd>
              </div>
              <div>
                <dt>Root hash</dt>
                <dd className="mono-break">{result.root_hash ?? "—"}</dd>
              </div>
              <div>
                <dt>Lean verified</dt>
                <dd>{result.lean_verified ? "yes" : "no"}</dd>
              </div>
              {claim?.statement && (
                <div>
                  <dt>Claim</dt>
                  <dd>{claim.statement}</dd>
                </div>
              )}
              {typeof certificate?.formal_theorem === "object" &&
                certificate.formal_theorem !== null &&
                "name" in certificate.formal_theorem && (
                  <div>
                    <dt>Theorem</dt>
                    <dd>
                      {String(
                        (certificate.formal_theorem as { name?: string }).name,
                      )}
                    </dd>
                  </div>
                )}
            </dl>
          </section>
        )}

        <section className="panel" aria-labelledby="history-heading">
          <h2 id="history-heading">Issued in this browser</h2>
          {history.length === 0 ? (
            <p className="note empty-hint" style={{ marginBottom: 0 }}>
              No certificates issued from this browser yet.
            </p>
          ) : (
            <ul className="project-list">
              {history.map((item) => (
                <li key={item.certificate_id}>
                  <span className="name">
                    {item.theorem ?? item.certificate_id.slice(0, 8)}
                    {item.lean_verified ? " · lean" : " · unverified"}
                  </span>
                  <span className="meta">
                    {new Date(item.issued_at).toLocaleString()}
                    {item.claim ? ` — ${item.claim}` : ""}
                    <br />
                    <span className="mono-break">{item.root_hash}</span>
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
