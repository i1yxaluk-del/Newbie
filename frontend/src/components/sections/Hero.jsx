import { DashboardWide } from "@/components/dashboards";

export default function Hero() {
  return (
    <section
      data-testid="hero-section"
      style={{ padding: "140px 0 100px", position: "relative", overflow: "hidden" }}
    >
      <div className="hero-texture" />
      <div className="wrap" style={{ position: "relative" }}>
        {/* Top: minimal — eyebrow, h1, one-line lead, 2 CTAs */}
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
            Ваша инфраструктура
            <br />
            работает.{" "}
            <em>
              Без
              <br />
              вашего участия.
            </em>
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
            Управляемый IT-сервис для российского бизнеса. Мониторинг, реакция по&nbsp;SLA,
            автоматические бэкапы — в&nbsp;одном договоре.
          </p>

          <div
            style={{
              display: "flex",
              gap: 12,
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            <a href="#audit" className="btn-core btn-primary" data-testid="hero-cta-primary">
              Получить бесплатный аудит →
            </a>
            <a href="#pricing" className="btn-core btn-secondary" data-testid="hero-cta-secondary">
              Смотреть тарифы
            </a>
          </div>
        </div>

        {/* Big dashboard preview — visual is the proof, no KPI duplicate below */}
        <div data-testid="hero-dashboard" style={{ maxWidth: 1180, margin: "0 auto" }}>
          <DashboardWide />
        </div>
      </div>
    </section>
  );
}
