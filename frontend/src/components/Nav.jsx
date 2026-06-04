import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, Phone } from "lucide-react";
import { useContent } from "@/content/useContent";

export default function Nav() {
  const content = useContent();
  const c = content.nav;
  const brand = content.meta.brand;
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      data-testid="main-nav"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        height: 60,
        display: "flex",
        alignItems: "center",
        background: "rgba(247,244,238,.92)",
        backdropFilter: "blur(16px) saturate(180%)",
        borderBottom: `1px solid ${scrolled ? "rgba(26,24,21,.12)" : "rgba(26,24,21,.06)"}`,
        transition: "border-color .3s",
      }}
    >
      <div
        className="wrap"
        style={{
          display: "flex",
          alignItems: "center",
          width: "100%",
        }}
      >
        <Link
          to="/"
          data-testid="nav-logo"
          style={{
            fontFamily: "var(--fd)",
            fontWeight: 600,
            fontSize: 20,
            letterSpacing: "-.01em",
            color: "var(--ink)",
            textDecoration: "none",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <ShieldCheck size={18} color="var(--forest)" strokeWidth={2.2} />
          {brand.name}{" "}
          <em style={{ color: "var(--forest)", fontStyle: "normal" }}>{brand.accent}</em>
        </Link>

        <div
          className="nav-links"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 28,
            marginLeft: "auto",
          }}
        >
          {c.links.map((l) => {
            const testid = `nav-${l.href.replace(/^#/, "")}`;
            return (
              <a
                key={l.href + l.label}
                href={l.href}
                data-testid={testid}
                className="hidden md:inline"
                style={{ fontSize: 14, color: "var(--stone)", textDecoration: "none" }}
              >
                {l.label}
              </a>
            );
          })}
          {c.phone && (
            <a
              href={`tel:${c.phone.replace(/[\s()\-–—]/g, "")}`}
              data-testid="nav-phone"
              className="hidden md:inline-flex"
              style={{
                fontSize: 13,
                color: "var(--stone)",
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                fontFamily: "var(--fm)",
                letterSpacing: ".02em",
              }}
            >
              <Phone size={13} color="var(--forest)" />
              {c.phone}
            </a>
          )}
          <a
            href={c.cta.href}
            data-testid="nav-cta-btn"
            className="btn-core btn-primary"
            style={{ padding: "9px 18px", fontSize: 13.5 }}
          >
            {c.cta.label}
          </a>
        </div>
      </div>
    </nav>
  );
}
