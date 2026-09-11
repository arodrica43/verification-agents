import Link from "next/link";

const links = [
  { href: "/studio", label: "Workspace" },
  { href: "/studio/certificates", label: "Certificates" },
];

export function StudioNav({
  active,
  contextLabel,
}: {
  active: "workspace" | "certificates";
  contextLabel?: string | null;
}) {
  return (
    <header className="studio-nav">
      <div className="studio-nav__left">
        <Link href="/" className="studio-nav__brand">
          Formal Platform
        </Link>
        {contextLabel ? (
          <span className="studio-nav__context" title={contextLabel}>
            {contextLabel}
          </span>
        ) : null}
      </div>
      <nav className="studio-nav__links" aria-label="Studio">
        {links.map((link) => {
          const isActive =
            (active === "workspace" && link.href === "/studio") ||
            (active === "certificates" &&
              link.href === "/studio/certificates");
          return (
            <Link
              key={link.href}
              href={link.href}
              className={isActive ? "is-active" : undefined}
              aria-current={isActive ? "page" : undefined}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
