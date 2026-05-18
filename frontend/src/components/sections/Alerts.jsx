import { TelegramAlert, WazuhAlerts } from "@/components/dashboards";
import { ServiceIcon } from "@/components/icons";

function ChannelBadge({ name, label }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "5px 10px 5px 8px",
        border: "1px solid rgba(255,255,255,.18)",
        borderRadius: 999,
        fontSize: 12,
        fontFamily: "var(--fm)",
        color: "rgba(241,237,228,.85)",
        background: "rgba(255,255,255,.04)",
        lineHeight: 1,
      }}
    >
      <ServiceIcon name={name} size={16} />
      {label}
    </span>
  );
}

export default function Alerts() {
  return (
    <section
      data-testid="alerts-section"
      id="alerts"
      style={{
        padding: "120px 0",
        background: "#0f0e0c",
        color: "#f1ede4",
        position: "relative",
      }}
    >
      <div className="wrap">
        <div style={{ maxWidth: 760, marginBottom: 56 }}>
          <div
            className="tag-dot"
            style={{ marginBottom: 18, color: "rgba(255,255,255,.65)" }}
          >
            Реагируем
          </div>
          <h2
            className="h-section"
            style={{
              marginBottom: 20,
              color: "#f5f1e8",
              fontSize: "clamp(36px, 4.4vw, 56px)",
            }}
          >
            Когда что-то ломается —
            <br />
            <em style={{ color: "#5fc9a2", fontStyle: "italic" }}>вы узнаёте первыми.</em>
          </h2>
          <p
            style={{
              fontSize: 17,
              color: "rgba(241,237,228,.65)",
              lineHeight: 1.6,
              maxWidth: 620,
              fontWeight: 300,
            }}
          >
            Алерты приходят в согласованные каналы связи с клиентом
            и нашей дежурной смены. Gold — плюс SIEM Wazuh
            с автоматической блокировкой подозрительных IP.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
            gap: 36,
          }}
          className="alerts-grid"
        >
          <div>
            <div
              className="tag-dot"
              style={{
                marginBottom: 16,
                color: "rgba(255,255,255,.50)",
                fontSize: 10,
              }}
            >
              Согласованные каналы · все тарифы
            </div>
            <div
              data-testid="alerts-channels"
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                marginBottom: 14,
              }}
            >
              <ChannelBadge name="telegram" label="Telegram" />
              <ChannelBadge name="max" label="MAX" />
            </div>
            <TelegramAlert />
            <p
              style={{
                marginTop: 14,
                fontSize: 13,
                color: "rgba(241,237,228,.55)",
                lineHeight: 1.55,
                fontFamily: "var(--fm)",
              }}
            >
              Кнопки ACK, silence, runbook — прямо из чата. MAX дублирует те же события (РФ-мессенджер, реестр Минцифры).
            </p>
          </div>

          <div>
            <div
              className="tag-dot"
              style={{
                marginBottom: 16,
                color: "rgba(255,255,255,.50)",
                fontSize: 10,
              }}
            >
              Wazuh SIEM · только Gold
            </div>
            <WazuhAlerts />
            <p
              style={{
                marginTop: 14,
                fontSize: 13,
                color: "rgba(241,237,228,.55)",
                lineHeight: 1.55,
                fontFamily: "var(--fm)",
              }}
            >
              brute-force · FIM · GPO change · PowerShell — журналируем для 152-ФЗ.
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          [data-testid="alerts-section"] .alerts-grid {
            grid-template-columns: 1fr !important;
            gap: 48px !important;
          }
        }
      `}</style>
    </section>
  );
}
