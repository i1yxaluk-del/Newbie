import { CheckCircle2, AlertTriangle, Server } from "lucide-react";

const MONITORS = [
  { host: "web-01", role: "Nginx · Ubuntu 22.04", status: "ok", uptime: "99.9%" },
  { host: "1c-01", role: "1С:Предприятие · Windows", status: "ok", uptime: "99.8%" },
  { host: "db-01", role: "PostgreSQL · Astra Linux", status: "ok", uptime: "99.7%" },
  { host: "file-01", role: "Samba · Ubuntu 22.04", status: "warn", uptime: "CPU 82%" },
];

export default function Hero() {
  return (
    <section
      data-testid="hero-section"
      style={{ padding: "140px 0 100px", position: "relative", overflow: "hidden" }}
    >
      <div className="hero-texture" />
      <div className="wrap" style={{ position: "relative" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) 420px",
            gap: 80,
            alignItems: "start",
          }}
          className="hero-grid-md"
        >
          <div>
            <div className="eyebrow" data-testid="hero-eyebrow">
              Управляемый IT-сервис · B2B · Россия · 2026
            </div>

            <h1 className="hero-h1" style={{ marginTop: 28, marginBottom: 28 }}>
              Ваша инфраструктура
              <br />
              работает. <em>Без вашего
              <br />
              участия.</em>
            </h1>

            <p
              style={{
                fontSize: 17,
                color: "var(--stone)",
                lineHeight: 1.75,
                maxWidth: 520,
                marginBottom: 44,
                fontWeight: 300,
              }}
              data-testid="hero-description"
            >
              Мониторинг серверов 24/7, автоматические бэкапы, реакция по SLA.
              Данные — в России (152-ФЗ), технологии — открытые и проверенные.
              Без штатного сисадмина и непредсказуемых счетов.
            </p>

            <div style={{ display: "flex", gap: 16, marginBottom: 60, flexWrap: "wrap" }}>
              <a
                href="#audit"
                className="btn-core btn-primary"
                data-testid="hero-cta-primary"
              >
                Получить бесплатный аудит →
              </a>
              <a
                href="#pricing"
                className="btn-core btn-ghost"
                data-testid="hero-cta-secondary"
              >
                Смотреть тарифы
              </a>
            </div>

            <div
              style={{
                display: "flex",
                gap: 36,
                paddingTop: 32,
                borderTop: "1px solid var(--rule)",
                flexWrap: "wrap",
              }}
            >
              {[
                ["24/7", "Мониторинг без выходных"],
                ["≤ 1 ч", "Реакция на P1 (Gold)"],
                ["AES-256", "Шифрование бэкапов"],
                ["РФ", "Данные в Yandex Cloud"],
              ].map(([num, label]) => (
                <div key={label}>
                  <div
                    className="font-display"
                    style={{ fontSize: 30, color: "var(--ink)", lineHeight: 1, marginBottom: 4 }}
                  >
                    {num}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--stone-lt)", letterSpacing: ".03em" }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Live dashboard card */}
          <div className="hero-card-wrap">
            <div
              data-testid="hero-monitor-card"
              style={{
                background: "#fff",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                padding: 28,
                boxShadow: "0 2px 24px rgba(26,24,21,.06), 0 0 0 1px rgba(27,77,62,.04)",
                position: "sticky",
                top: 84,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 20,
                  paddingBottom: 14,
                  borderBottom: "1px solid var(--rule-lt)",
                }}
              >
                <span className="pulse-dot" />
                <span
                  className="font-mono"
                  style={{
                    fontSize: 10.5,
                    letterSpacing: ".12em",
                    textTransform: "uppercase",
                    color: "var(--stone)",
                  }}
                >
                  Мониторинг · live
                </span>
              </div>

              {MONITORS.map((m) => (
                <div
                  key={m.host}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 0",
                    borderBottom: "1px solid var(--rule-lt)",
                    fontSize: 13.5,
                  }}
                >
                  <div>
                    <div
                      style={{
                        color: "var(--ink)",
                        fontWeight: 500,
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <Server size={12} color="var(--stone-lt)" />
                      {m.host}
                    </div>
                    <div style={{ color: "var(--stone-lt)", fontSize: 12, marginTop: 2 }}>
                      {m.role}
                    </div>
                  </div>
                  <div
                    className="font-mono"
                    style={{
                      fontSize: 11,
                      display: "flex",
                      alignItems: "center",
                      gap: 5,
                      color: m.status === "ok" ? "var(--forest)" : "var(--amber)",
                    }}
                  >
                    {m.status === "ok" ? (
                      <CheckCircle2 size={12} />
                    ) : (
                      <AlertTriangle size={12} />
                    )}
                    {m.status === "ok" ? `UP · ${m.uptime}` : m.uptime}
                  </div>
                </div>
              ))}

              <div
                style={{
                  marginTop: 18,
                  padding: "12px 14px",
                  background: "var(--forest-dim)",
                  border: "1px solid var(--forest-bdr)",
                  borderRadius: 4,
                  fontSize: 13,
                  color: "var(--forest)",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span style={{ fontWeight: 500 }}>Все 4 сервера под контролем</span>
                <span className="font-mono" style={{ fontSize: 12 }}>
                  обновлено 23с назад
                </span>
              </div>

              <div
                className="font-mono"
                style={{
                  marginTop: 10,
                  padding: "10px 14px",
                  background: "var(--cream)",
                  borderRadius: 4,
                  fontSize: 12,
                  color: "var(--stone)",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span>Последний бэкап</span>
                <span>Сегодня 03:47 · 5.2 ГБ ✓</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) {
          .hero-grid-md { grid-template-columns: 1fr !important; gap: 48px !important; }
          .hero-card-wrap { display: none; }
        }
      `}</style>
    </section>
  );
}
