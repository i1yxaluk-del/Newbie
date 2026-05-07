// Telegram alert card — how the client sees a P1 incident notification.
// Chat-bubble look, dark or light variant.

const C = {
  ink: "#0e0c0a",
  inkLt: "#1f1d1a",
  stone: "#7a7a7a",
  stoneLt: "#a1a1a1",
  rule: "rgba(255,255,255,.08)",
  ruleLt: "rgba(255,255,255,.04)",
  bg: "#181715",
  bgCard: "#22201d",
  blue: "#5ea7ea",
  red: "#e7625f",
  amber: "#e8b75f",
  forest: "#5fc9a2",
};

export default function TelegramAlert() {
  return (
    <div
      data-testid="telegram-alert"
      style={{
        background: C.bg,
        border: `1px solid ${C.rule}`,
        borderRadius: 8,
        padding: 0,
        overflow: "hidden",
        color: "#fff",
        fontFamily: "var(--fb)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "12px 16px",
          background: C.inkLt,
          borderBottom: `1px solid ${C.rule}`,
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #5ea7ea, #2d6b58)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          МО
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.2 }}>
            МСП Облако · alerts
          </div>
          <div style={{ fontSize: 11, color: C.stoneLt, marginTop: 2 }}>
            on-call · сейчас в сети
          </div>
        </div>
        <div style={{ fontSize: 11, color: C.stoneLt }}>03:47</div>
      </div>

      {/* Chat */}
      <div
        style={{
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          minHeight: 220,
        }}
      >
        {/* System notice */}
        <div
          style={{
            alignSelf: "center",
            fontSize: 11,
            color: C.stoneLt,
            background: "rgba(255,255,255,.04)",
            padding: "4px 10px",
            borderRadius: 10,
            margin: "4px 0 8px",
          }}
        >
          7 мая 2026
        </div>

        {/* Alert message bubble */}
        <div
          style={{
            background: C.bgCard,
            borderLeft: `3px solid ${C.red}`,
            padding: "12px 14px",
            borderRadius: "10px 10px 10px 2px",
            maxWidth: "92%",
          }}
        >
          <div
            style={{
              fontFamily: "var(--fm)",
              fontSize: 10,
              letterSpacing: ".10em",
              color: C.red,
              textTransform: "uppercase",
              fontWeight: 600,
              marginBottom: 6,
            }}
          >
            🔴 P1 · alert · prod
          </div>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>
            web-01 · 5xx errors {">"}0.5% за 2 мин
          </div>
          <div
            style={{
              fontFamily: "var(--fm)",
              fontSize: 12,
              color: C.stoneLt,
              lineHeight: 1.55,
              whiteSpace: "pre-wrap",
            }}
          >
            severity: P1{"\n"}
            host: web-01.client-llc{"\n"}
            metric: rate(http_5xx[2m]) = 1.8%{"\n"}
            runbook: docs/R-04
          </div>
          <div
            style={{
              display: "flex",
              gap: 8,
              marginTop: 12,
              paddingTop: 10,
              borderTop: `1px solid ${C.rule}`,
            }}
          >
            <ChatBtn label="ACK · взять" primary />
            <ChatBtn label="silence 30m" />
            <ChatBtn label="runbook" />
          </div>
          <div
            style={{
              fontSize: 10,
              color: C.stoneLt,
              marginTop: 8,
              fontFamily: "var(--fm)",
              letterSpacing: ".04em",
            }}
          >
            03:47:12 · alertmanager
          </div>
        </div>

        {/* Engineer reply */}
        <div
          style={{
            alignSelf: "flex-end",
            background: "linear-gradient(135deg, #2d6b58, #1b4d3e)",
            padding: "10px 14px",
            borderRadius: "10px 10px 2px 10px",
            maxWidth: "70%",
            fontSize: 13,
          }}
        >
          ack, смотрю
          <div
            style={{
              fontSize: 10,
              color: "rgba(255,255,255,.7)",
              marginTop: 4,
              textAlign: "right",
            }}
          >
            03:49 ✓✓
          </div>
        </div>

        {/* Resolved system message */}
        <div
          style={{
            alignSelf: "center",
            fontSize: 11,
            color: C.forest,
            background: "rgba(95,201,162,.10)",
            border: `1px solid rgba(95,201,162,.25)`,
            padding: "4px 12px",
            borderRadius: 10,
            marginTop: 4,
          }}
        >
          ✓ resolved · 04:32 · MTTR 45m
        </div>
      </div>
    </div>
  );
}

function ChatBtn({ label, primary }) {
  return (
    <button
      type="button"
      style={{
        flex: 1,
        background: primary ? "rgba(94,167,234,.15)" : "rgba(255,255,255,.06)",
        color: primary ? "#5ea7ea" : "#c9c5be",
        border: "none",
        borderRadius: 6,
        padding: "8px 4px",
        fontFamily: "var(--fm)",
        fontSize: 11,
        cursor: "pointer",
        fontWeight: 500,
      }}
    >
      {label}
    </button>
  );
}
