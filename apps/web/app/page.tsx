import Link from "next/link";

export default function HomePage() {
  return (
    <main className="landing">
      <div className="landing__grid" aria-hidden />
      <div className="landing__noise" aria-hidden />
      <div className="landing__frame">
        <div className="landing__top">
          <span className="landing__mark">Verification studio</span>
          <Link href="/studio">Open studio</Link>
        </div>
        <div className="landing__hero">
          <p className="landing__brand">
            Formal
            <span>Platform</span>
          </p>
          <div className="landing__rule" aria-hidden />
          <h1 className="landing__headline">
            Prove claims. Bind evidence. Issue certificates.
          </h1>
          <p className="landing__lede">
            A technical studio for AI-assisted formal reasoning — Lean proofs,
            provenance graphs, and verifiable certificates in one workspace.
          </p>
          <Link className="landing__cta" href="/studio">
            Enter studio
            <span aria-hidden>→</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
