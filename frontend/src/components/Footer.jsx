import { ShieldCheck, Phone } from "lucide-react";
import { useContent } from "@/content/useContent";

export default function Footer() {
  const content = useContent();
  const c = content.footer;
  const brand = content.meta.brand;
  return (
    <footer
      data-testid="main-footer"
      style={{
        borderTop: "1px solid var(--rule)",
        padding: "40px 0",
        background: "var(--cream)",
      }}
    >
      <div className="wrap">
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 24,
            flexWrap: "wrap",
          }}
        >
          <div style={{ maxWidth: 340 }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                fontFamily: "var(--fd)",
                fontSize: 18,
                fontWeight: 500,
                color: "var(--ink)",
              }}
            >
              <ShieldCheck size={16} color="var(--forest)" />
              {brand.name}{" "}
              <em style={{ color: "var(--forest)", fontStyle: "normal" }}>{brand.accent}</em>
            </div>
            <p
              style={{
                fontSize: 12.5,
                color: "var(--stone-lt)",
                lineHeight: 1.6,
                marginTop: 10,
              }}
            >
              {c.tagline}
              <br />
              <span style={{ opacity: 0.6 }}>{c.legal}</span>
            </p>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              fontSize: 13,
            }}
          >
            <span
              className="font-mono"
              style={{
                fontSize: 10.5,
                letterSpacing: ".12em",
                textTransform: "uppercase",
                color: "var(--stone-lt)",
                marginBottom: 4,
              }}
            >
              {c.docsLabel}
            </span>
            {c.docs.map((d, i) => {
              const slug = (d.href.match(/([\w-]+)\.html$/) || [])[1] || `doc-${i}`;
              return (
                <a
                  key={d.href}
                  href={d.href}
                  data-testid={`footer-${slug}`}
                  style={{ color: "var(--stone)", textDecoration: "none" }}
                >
                  {d.label}
                </a>
              );
            })}
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              fontSize: 13,
            }}
          >
            <span
              className="font-mono"
              style={{
                fontSize: 10.5,
                letterSpacing: ".12em",
                textTransform: "uppercase",
                color: "var(--stone-lt)",
                marginBottom: 4,
              }}
            >
              {c.contactsLabel}
            </span>
            <a
              href={`mailto:${c.email}`}
              data-testid="footer-email"
              style={{ color: "var(--stone)", textDecoration: "none" }}
            >
              {c.email}
            </a>
            <a
              href={c.telegram.href}
              data-testid="footer-tg"
              style={{ color: "var(--forest)", textDecoration: "none", fontFamily: "var(--fm)" }}
            >
              {c.telegram.label}
            </a>
            {c.max?.href && (
              <a
                href={c.max.href}
                data-testid="footer-max"
                style={{ color: "var(--forest)", textDecoration: "none", fontFamily: "var(--fm)" }}
              >
                {c.max.label}
              </a>
            )}
          </div>
        </div>
      </div>
    </footer>
  );
}
