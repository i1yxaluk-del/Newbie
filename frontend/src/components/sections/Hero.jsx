import { DashboardWide } from "@/components/dashboards";
import { useContent } from "@/content/useContent";

export default function Hero() {
  const c = useContent().hero;
  return (
    <section
      data-testid="hero-section"
      style={{ padding: "140px 0 100px", position: "relative", overflow: "hidden" }}
    >
      <div className="hero-texture" />
      <div className="wrap" style={{ position: "relative" }}>
        <div style={{ maxWidth: 920, margin: "0 auto 72px", textAlign: "center" }}>
          <h1
            className="hero-h1"
            data-testid="hero-h1"
            style={{
              marginBottom: 24,
              fontSize: "clamp(52px, 7.5vw, 96px)",
              letterSpacing: "-.035em",
              lineHeight: 1.02,
            }}
          >
            {c.h1Before} <em>{c.h1Em}</em>
          </h1>

          <p
            data-testid="hero-description"
            className="hero-lead"
            style={{
              margin: "0 auto 44px",
              maxWidth: 540,
              fontSize: 17,
              color: "var(--ink-2)",
              opacity: 0.7,
              lineHeight: 1.55,
              fontWeight: 400,
            }}
          >
            {c.lead}
          </p>

          <div
            style={{
              display: "flex",
              gap: 12,
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            <a
              href={c.ctaPrimary.href}
              className="btn-core btn-primary"
              data-testid="hero-cta-primary"
            >
              {c.ctaPrimary.label}
            </a>
            <a
              href={c.ctaSecondary.href}
              className="btn-core btn-secondary"
              data-testid="hero-cta-secondary"
            >
              {c.ctaSecondary.label}
            </a>
          </div>
        </div>

        <div data-testid="hero-dashboard" style={{ maxWidth: 1180, margin: "0 auto" }}>
          <DashboardWide />
        </div>
      </div>
    </section>
  );
}
