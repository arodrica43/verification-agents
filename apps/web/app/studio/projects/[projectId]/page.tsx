"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { StudioNav } from "@/components/studio-nav";
import { ApiError, apiFetch } from "@/lib/api";
import type { AgentRun, AgentRunSummary, Project } from "@/lib/types";

const PIPELINE: { graph: AgentRun["graph"]; label: string; needsText?: boolean }[] = [
  { graph: "problem_modelling", label: "1. Model system", needsText: true },
  { graph: "formalization", label: "2. Formalize claims" },
  { graph: "proof", label: "3. Propose proof" },
  { graph: "certification", label: "4. Prepare certificate" },
];

export default function ProjectStudioPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
  const [latest, setLatest] = useState<AgentRun | null>(null);
  const [problemText, setProblemText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(
    null,
  );
  const [bootError, setBootError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [proj, runList] = await Promise.all([
      apiFetch<Project>(`/api/v1/projects/${encodeURIComponent(projectId)}`),
      apiFetch<{ items: AgentRunSummary[] }>(
        `/api/v1/projects/${encodeURIComponent(projectId)}/agent-runs`,
      ),
    ]);
    setProject(proj);
    setRuns(runList.items ?? []);
    if (runList.items?.[0]?.run_id) {
      const run = await apiFetch<AgentRun>(
        `/api/v1/agents/runs/${encodeURIComponent(runList.items[0].run_id)}`,
      );
      setLatest(run);
      if (run.problem_text) setProblemText(run.problem_text);
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await refresh();
      } catch (err) {
        if (!cancelled) {
          setBootError(
            err instanceof ApiError ? err.message : "Failed to load project.",
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  async function runGraph(graph: AgentRun["graph"]) {
    if (!project) return;
    setBusy(true);
    setMessage(null);
    try {
      const seed =
        latest && latest.status === "completed" ? latest.run_id : undefined;
      const body: Record<string, unknown> = {
        organization_id: project.organization_id,
        workspace_id: project.workspace_id,
        project_id: project.id,
        graph,
        problem_text: problemText,
        lean_verified: latest?.lean_verified ?? false,
      };
      if (graph !== "problem_modelling" && seed) {
        body.seed_from_run_id = seed;
      }
      const run = await apiFetch<AgentRun>("/api/v1/agents/runs", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setLatest(run);
      setMessage({
        tone: "ok",
        text:
          run.status === "interrupted"
            ? `Paused for review at ${run.interrupt_node ?? "gate"}.`
            : `Finished ${graph} (${run.status}).`,
      });
      await refresh();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Agent run failed.",
      });
    } finally {
      setBusy(false);
    }
  }

  async function issueDemoCert() {
    setBusy(true);
    setMessage(null);
    try {
      const data = await apiFetch<{
        certificate_id?: string;
        lean_verified?: boolean;
      }>("/api/v1/certificates/demo/issue", {
        method: "POST",
        body: JSON.stringify({ allow_unverified: true, require_lean: false }),
      });
      setMessage({
        tone: "ok",
        text: `Demo certificate ${data.certificate_id ?? ""} issued (lean=${Boolean(data.lean_verified)}). See Certificates tab for history.`,
      });
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Certificate issue failed.",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <StudioNav
        active="workspace"
        contextLabel={project ? project.name : null}
      />
      <main className="studio-main">
        <p className="note" style={{ marginTop: 0 }}>
          <Link href="/studio">← Back to workspace</Link>
        </p>
        {bootError && (
          <p className="status status--error" role="alert">
            {bootError}
          </p>
        )}
        {project && (
          <>
            <h1>{project.name}</h1>
            <p className="lede">
              Describe the system, run modelling → formalization → proof agents,
              then issue a certificate. Lean remains the only verifier of truth.
            </p>
            {project.description ? (
              <p className="note">{project.description}</p>
            ) : null}

            <section className="panel" aria-labelledby="system-heading">
              <h2 id="system-heading">System &amp; properties</h2>
              <form
                className="form-grid"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  void runGraph("problem_modelling");
                }}
              >
                <label>
                  Natural-language description
                  <textarea
                    rows={6}
                    required
                    value={problemText}
                    onChange={(e) => setProblemText(e.target.value)}
                    placeholder={
                      "Example: An AgentRuntime must not complete a PrivilegedAction unless Authorization holds under Policy."
                    }
                  />
                </label>
                <div className="form-actions">
                  {PIPELINE.map((step) => (
                    <button
                      key={step.graph}
                      type="button"
                      className={
                        step.graph === "problem_modelling"
                          ? "btn btn-primary"
                          : "btn"
                      }
                      disabled={
                        busy ||
                        (step.needsText && !problemText.trim()) ||
                        (step.graph !== "problem_modelling" && !latest)
                      }
                      onClick={() => void runGraph(step.graph)}
                    >
                      {step.label}
                    </button>
                  ))}
                </div>
              </form>
              {message && (
                <p className={`status status--${message.tone}`} role="status">
                  {message.text}
                </p>
              )}
            </section>

            {latest && (
              <section className="panel" aria-labelledby="result-heading">
                <h2 id="result-heading">
                  Latest run · {latest.graph} · {latest.status}
                </h2>
                {latest.entities.length > 0 && (
                  <>
                    <h3 className="subhead">Entities</h3>
                    <ul className="feature-list">
                      {latest.entities.map((e) => (
                        <li key={String(e.id)} className="on">
                          {String(e.name ?? e.id)}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {latest.assumptions.length > 0 && (
                  <>
                    <h3 className="subhead">Assumptions</h3>
                    <ul className="project-list">
                      {latest.assumptions.map((a) => (
                        <li key={String(a.id)}>
                          <span className="name">{String(a.id)}</span>
                          <span className="meta">{String(a.statement ?? "")}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {latest.goals.length > 0 && (
                  <>
                    <h3 className="subhead">Goals / properties</h3>
                    <ul className="project-list">
                      {latest.goals.map((g) => (
                        <li key={String(g.id)}>
                          <span className="name">{String(g.kind ?? g.id)}</span>
                          <span className="meta">{String(g.statement ?? "")}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {latest.claims.length > 0 && (
                  <>
                    <h3 className="subhead">Claims</h3>
                    <ul className="project-list">
                      {latest.claims.map((c) => (
                        <li key={String(c.id)}>
                          <span className="name">{String(c.id)}</span>
                          <span className="meta">{String(c.statement ?? "")}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {latest.lean_skeleton && (
                  <>
                    <h3 className="subhead">Lean skeleton (not verified)</h3>
                    <pre className="code-block">{latest.lean_skeleton}</pre>
                  </>
                )}
                {latest.candidate_proof && (
                  <>
                    <h3 className="subhead">Candidate proof</h3>
                    <pre className="code-block">
                      {JSON.stringify(latest.candidate_proof, null, 2)}
                    </pre>
                  </>
                )}
                <p className="note">
                  lean_verified={String(latest.lean_verified)} · certificate_ready=
                  {String(latest.certificate_ready)} · history:{" "}
                  {latest.history.join(" → ") || "—"}
                </p>
              </section>
            )}

            <section className="panel" aria-labelledby="cert-heading">
              <h2 id="cert-heading">Certificate</h2>
              <p className="note">
                Independent Lean verification is required for production
                certificates. For local demos you can still issue the agent-policy
                demo bundle.
              </p>
              <div className="form-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() => void issueDemoCert()}
                >
                  Issue demo certificate
                </button>
                <Link className="btn" href="/studio/certificates">
                  Open certificates
                </Link>
              </div>
            </section>

            <section className="panel" aria-labelledby="history-heading">
              <h2 id="history-heading">Agent runs</h2>
              {runs.length === 0 ? (
                <p className="note empty-hint">No agent runs yet.</p>
              ) : (
                <ul className="project-list">
                  {runs.map((r) => (
                    <li key={r.run_id}>
                      <span className="name">
                        {r.graph} · {r.status}
                      </span>
                      <span className="meta">
                        {r.updated_at ?? r.created_at ?? r.run_id}
                        {r.pending_human_review ? " · needs review" : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </main>
    </>
  );
}
