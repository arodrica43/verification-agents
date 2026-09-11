"use client";

import { useState } from "react";
import { StudioNav } from "@/components/studio-nav";
import { ApiError, apiFetch, getApiUrl } from "@/lib/api";
import type { DemoCertificateIssue } from "@/lib/types";

export default function CertificatesPage() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<DemoCertificateIssue | null>(null);
  const [message, setMessage] = useState<{
    tone: "ok" | "error" | "warn";
    text: string;
  } | null>(null);

  async function issueDemo() {
    setBusy(true);
    setMessage(null);
    const requireLean =
      (process.env.NEXT_PUBLIC_REQUIRE_LEAN ?? "false").toLowerCase() === "true";
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
      setMessage({
        tone: "ok",
        text: data.lean_verified
          ? "Demo certificate issued with Lean verification."
          : "Demo certificate issued (Lean not required for this local demo).",
      });
    } catch (err) {
      setResult(null);
      const text =
        err instanceof ApiError
          ? err.message
          : "Failed to issue demo certificate.";
      setMessage({
        tone: "error",
        text:
          text +
          " If Lean is required by the API defaults, keep allow_unverified: true and require_lean: false for local demos, or install Lean and set require_lean: true.",
      });
    } finally {
      setBusy(false);
    }
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
      <StudioNav active="certificates" />
      <main className="studio-main">
        <h1>Certificates</h1>
        <p className="lede">
          Issue and inspect the agent-policy demo certificate against{" "}
          <code>{getApiUrl()}</code>.
        </p>

        <section className="panel" aria-labelledby="issue-heading">
          <h2 id="issue-heading">Demo issue</h2>
          <p className="note">
            Local demo posts{" "}
            <code>
              {`{ allow_unverified: true, require_lean: false }`}
            </code>{" "}
            so issuance works without a Lean toolchain. Production-style checks
            should set <code>require_lean: true</code> and run an independent
            Lean verify.
          </p>
          <div className="form-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void issueDemo()}
              disabled={busy}
            >
              {busy ? "Issuing…" : "Issue demo certificate"}
            </button>
          </div>
          {message && (
            <p className={`status status--${message.tone}`} role="status">
              {message.text}
            </p>
          )}
        </section>

        {result && (
          <section className="panel" aria-labelledby="result-heading">
            <h2 id="result-heading">Issued certificate</h2>
            <dl className="cert-summary">
              <div>
                <dt>Certificate ID</dt>
                <dd>{result.certificate_id ?? "—"}</dd>
              </div>
              <div>
                <dt>Root hash</dt>
                <dd>{result.root_hash ?? "—"}</dd>
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

        {!result && (
          <section className="panel" aria-labelledby="info-heading">
            <h2 id="info-heading">What you get</h2>
            <p className="note" style={{ marginBottom: 0 }}>
              The demo bundle includes <code>certificate.json</code>, provenance
              edges, HMAC signatures, and a verification report. Use this page
              to confirm the API issuer path before wiring Lean-gated CI.
            </p>
          </section>
        )}
      </main>
    </>
  );
}
