import { LatencyChart } from "@/components/dashboards";

export default function Visibility() {
  return (
    <section
      data-testid="visibility-section"
      id="visibility"
      style={{
        padding: "120px 0",
        background: "#fff",
        borderTop: "1px solid var(--rule-lt)",
        borderBottom: "1px solid var(--rule-lt)",
      }}
    >
      <div className="wrap">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
            gap: 80,
            alignItems: "center",
          }}
          className="visibility-grid"
        >
          <div>
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              Видим
            </div>
            <h2 className="h-section" style={{ marginBottom: 20 }}>
              Один <em>дашборд</em>
              <br />
              на всю инфраструктуру.
            </h2>
            <p className="section-lead" style={{ marginBottom: 32 }}>
              Метрики, логи, алерты и SLA в одном Grafana-окне. Латентность,
              ошибки 5xx, нагрузка на 1С, репликация AD, состояние
              файловых шар — без переключения между 5 разными интерфейсами.
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 14 }}>
              {[
                "Prometheus + Grafana — метрики каждые 15 с",
                "Loki — централизованные логи с фильтрами",
                "Алерты в Telegram, email, дежурного on-call",
                "Доступ для клиента — read-only, отдельный логин",
              ].map((it) => (
                <li
                  key={it}
                  style={{
                    display: "flex",
                    gap: 12,
                    fontSize: 14.5,
                    color: "var(--ink-2)",
                    lineHeight: 1.5,
                  }}
                >
                  <span
                    style={{
                      flex: "0 0 auto",
                      width: 16,
                      height: 1,
                      background: "var(--forest)",
                      marginTop: 11,
                    }}
                  />
                  {it}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <LatencyChart />
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .visibility-grid { grid-template-columns: 1fr !important; gap: 48px !important; }
        }
      `}</style>
    </section>
  );
}
