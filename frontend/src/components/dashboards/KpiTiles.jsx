// 3 KPI tiles for CTAForm: "what you get after onboarding".

const C = {
  ink: "#1a1815",
  stone: "#78746a",
  stoneLt: "#a8a49c",
  rule: "rgba(26,24,21,.10)",
  forest: "#1b4d3e",
};

const TILES = [
  { label: "Uptime", value: "99.9", unit: "%", note: "Цель Bronze" },
  { label: "MTTR P1", value: "≤ 60", unit: "мин", note: "Цель Silver" },
  { label: "Backup age", value: "< 24", unit: "ч", note: "Verify ежедневно" },
];

export default function KpiTiles() {
  return (
    <div
      data-testid="kpi-tiles"
      style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}
    >
      {TILES.map((t) => (
        <div
          key={t.label}
          style={{
            border: `1px solid ${C.rule}`,
            borderRadius: 6,
            padding: "12px 14px",
            background: "#fff",
          }}
        >
          <div
            style={{
              fontFamily: "var(--fm)",
              fontSize: 9.5,
              letterSpacing: ".10em",
              textTransform: "uppercase",
              color: C.stone,
              marginBottom: 6,
            }}
          >
            {t.label}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 3 }}>
            <span
              style={{
                fontFamily: "var(--fd)",
                fontSize: 22,
                fontWeight: 500,
                color: C.forest,
                lineHeight: 1,
                letterSpacing: "-.02em",
              }}
            >
              {t.value}
            </span>
            <span style={{ fontSize: 11, color: C.stoneLt }}>{t.unit}</span>
          </div>
          <div
            style={{
              fontFamily: "var(--fm)",
              fontSize: 9.5,
              color: C.stoneLt,
              marginTop: 4,
              letterSpacing: ".04em",
            }}
          >
            {t.note}
          </div>
        </div>
      ))}
    </div>
  );
}
