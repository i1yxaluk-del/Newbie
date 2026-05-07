import { DashboardWide } from "@/components/dashboards";

export default function Hero() {
  return (
    <section
      data-testid="hero-section"
      style={{ padding: "120px 0 80px", position: "relative", overflow: "hidden" }}
    >
      <div className="hero-texture" />
      <div className="wrap" style={{ position: "relative" }}>
        {/* Top: centered big heading + subtitle + CTAs */}
        <div style={{ maxWidth: 880, margin: "0 auto", textAlign: "center" }}>
          <div
            className="eyebrow"
            data-testid="hero-eyebrow"
            style={{ justifyContent: "center", marginBottom: 28 }}
          >
            Управляемый IT-сервис · B2B · Россия · 2026
          </div>

          <h1
            className="hero-h1"
            style={{ marginBottom: 24, fontSize: "clamp(48px, 7vw, 88px)", letterSpacing: "-.03em" }}
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

          <ul
            data-testid="hero-description"
            className="hero-pillars"
            style={{
              listStyle: "none",
              padding: 0,
              margin: "0 auto 40px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              fontSize: 17,
              color: "var(--stone)",
              fontWeight: 300,
              lineHeight: 1.4,
            }}
          >
            {[
              "Мониторинг 24/7",
              "Реакция по SLA",
              "Автоматические бэкапы",
              "Защита инфраструктуры",
              "Восстановление по MTTR",
            ].map((p) => (
              <li
                key={p}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <span
                  aria-hidden="true"
                  style={{
                    flex: "0 0 auto",
                    width: 18,
                    height: 1,
                    background: "var(--forest)",
                    opacity: 0.55,
                  }}
                />
                {p}
              </li>
            ))}
          </ul>

          <div
            style={{
              display: "flex",
              gap: 12,
              marginBottom: 64,
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

        {/* Big dashboard preview, full-width below text */}
        <div data-testid="hero-dashboard" style={{ maxWidth: 1080, margin: "0 auto" }}>
          <DashboardWide />
        </div>

        {/* KPI strip below dashboard */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 0,
            marginTop: 48,
            paddingTop: 36,
            borderTop: "1px solid var(--rule)",
          }}
          className="hero-kpis"
        >
          {[
            ["24/7", "Мониторинг 365 дней"],
            ["≤ 60 мин", "Реакция P1 (Gold)"],
            ["AES-256", "Шифрование бэкапов"],
            ["РФ", "Дата-центры в РФ"],
          ].map(([num, label], i) => (
            <div
              key={label}
              style={{
                textAlign: "center",
                padding: "0 12px",
                borderRight:
                  i < 3 ? "1px solid var(--rule-lt)" : "none",
              }}
            >
              <div
                className="font-display"
                style={{
                  fontSize: 36,
                  color: "var(--ink)",
                  lineHeight: 1,
                  marginBottom: 8,
                  letterSpacing: "-.02em",
                }}
              >
                {num}
              </div>
              <div
                style={{
                  fontFamily: "var(--fm)",
                  fontSize: 11,
                  color: "var(--stone-lt)",
                  letterSpacing: ".06em",
                  textTransform: "uppercase",
                }}
              >
                {label}
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 720px) {
          .hero-kpis { grid-template-columns: repeat(2, 1fr) !important; gap: 24px 0 !important; }
          .hero-kpis > div { border-right: none !important; }
        }
      `}</style>
    </section>
  );
}
