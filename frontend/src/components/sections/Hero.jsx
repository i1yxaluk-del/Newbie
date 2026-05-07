import { useState } from "react";
import { GoldenSignals, SlaTimeline, BackupHealth } from "@/components/dashboards";

const TABS = [
  { id: "see", label: "Видим", caption: "Мониторинг + логи" },
  { id: "react", label: "Реагируем", caption: "SLA · on-call" },
  { id: "save", label: "Сохраняем", caption: "Бэкапы · DR" },
];

function TabPanel({ active }) {
  if (active === "see") return <GoldenSignals />;
  if (active === "react") return <SlaTimeline />;
  return <BackupHealth />;
}

export default function Hero() {
  const [active, setActive] = useState("see");

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
            gridTemplateColumns: "minmax(0,1fr) minmax(0, 480px)",
            gap: 64,
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
              Открытый стек (Prometheus · Grafana · Wazuh · Restic), РФ ПО для
              соответствия 152-ФЗ. Без штатного сисадмина и непредсказуемых счетов.
            </p>

            <div style={{ display: "flex", gap: 16, marginBottom: 60, flexWrap: "wrap" }}>
              <a href="#audit" className="btn-core btn-primary" data-testid="hero-cta-primary">
                Получить бесплатный аудит →
              </a>
              <a href="#pricing" className="btn-core btn-ghost" data-testid="hero-cta-secondary">
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

          {/* Tabbed dashboard centerpiece */}
          <div className="hero-card-wrap" data-testid="hero-dashboard">
            <div
              style={{
                position: "sticky",
                top: 84,
                background: "rgba(255,255,255,.6)",
                backdropFilter: "blur(6px)",
                border: "1px solid var(--rule)",
                borderRadius: 10,
                padding: 14,
                boxShadow:
                  "0 2px 24px rgba(26,24,21,.06), 0 0 0 1px rgba(27,77,62,.04)",
              }}
            >
              {/* Tab strip */}
              <div
                role="tablist"
                style={{
                  display: "flex",
                  gap: 4,
                  padding: 4,
                  background: "var(--cream)",
                  borderRadius: 6,
                  marginBottom: 12,
                }}
              >
                {TABS.map((t) => {
                  const isActive = active === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      role="tab"
                      aria-selected={isActive}
                      data-testid={`hero-tab-${t.id}`}
                      onClick={() => setActive(t.id)}
                      style={{
                        flex: 1,
                        border: "none",
                        background: isActive ? "#fff" : "transparent",
                        color: isActive ? "var(--ink)" : "var(--stone)",
                        boxShadow: isActive ? "0 1px 2px rgba(26,24,21,.08)" : "none",
                        padding: "8px 10px",
                        borderRadius: 4,
                        fontFamily: "var(--fb)",
                        fontWeight: 500,
                        fontSize: 13,
                        cursor: "pointer",
                        textAlign: "left",
                        transition: "background .15s, color .15s",
                      }}
                    >
                      <div>{t.label}</div>
                      <div
                        style={{
                          fontFamily: "var(--fm)",
                          fontSize: 9.5,
                          color: isActive ? "var(--stone)" : "var(--stone-lt)",
                          letterSpacing: ".05em",
                          textTransform: "uppercase",
                          marginTop: 2,
                        }}
                      >
                        {t.caption}
                      </div>
                    </button>
                  );
                })}
              </div>
              <div role="tabpanel" data-testid={`hero-panel-${active}`}>
                <TabPanel active={active} />
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) {
          .hero-grid-md { grid-template-columns: 1fr !important; gap: 48px !important; }
          .hero-card-wrap > div { position: static !important; }
        }
      `}</style>
    </section>
  );
}
