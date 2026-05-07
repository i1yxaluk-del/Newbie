// SLA / on-call response timeline for "Реагируем" pillar.

const C = {
  ink: "#1a1815",
  stone: "#78746a",
  stoneLt: "#a8a49c",
  rule: "rgba(26,24,21,.10)",
  ruleLt: "rgba(26,24,21,.05)",
  forest: "#1b4d3e",
  forestLt: "#2d6b58",
  amber: "#b45309",
};

const EVENTS = [
  { t: "00:00", label: "P1 alert", desc: "5xx >0.5%", color: C.amber },
  { t: "+02 мин", label: "ACK", desc: "on-call ответил", color: C.forestLt },
  { t: "+18 мин", label: "Fix", desc: "rollback nginx", color: C.forest },
  { t: "+45 мин", label: "Verify", desc: "ok 30 мин", color: C.forest },
];

export default function SlaTimeline() {
  return (
    <div
      data-testid="sla-timeline"
      style={{
        background: "#fff",
        border: `1px solid ${C.rule}`,
        borderRadius: 8,
        padding: 20,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 18,
          paddingBottom: 12,
          borderBottom: `1px solid ${C.ruleLt}`,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div>
          <div
            style={{
              fontFamily: "var(--fm)",
              fontSize: 10,
              letterSpacing: ".10em",
              textTransform: "uppercase",
              color: C.stone,
            }}
          >
            SLA · последний инцидент
          </div>
          <div
            style={{
              fontFamily: "var(--fd)",
              fontSize: 22,
              fontWeight: 500,
              color: C.ink,
              marginTop: 2,
            }}
          >
            MTTR <span style={{ color: C.forest }}>45 мин</span>{" "}
            <span style={{ fontSize: 14, color: C.stoneLt }}>· цель ≤ 60 мин</span>
          </div>
        </div>
        <div
          style={{
            padding: "6px 12px",
            background: "rgba(27,77,62,.08)",
            borderRadius: 4,
            fontFamily: "var(--fm)",
            fontSize: 11,
            color: C.forest,
            letterSpacing: ".05em",
            textTransform: "uppercase",
          }}
        >
          Resolved
        </div>
      </div>

      <div style={{ position: "relative", padding: "20px 0 8px" }}>
        <div
          style={{
            position: "absolute",
            top: 28,
            left: 16,
            right: 16,
            height: 2,
            background: C.ruleLt,
          }}
        />
        <div
          style={{
            position: "relative",
            display: "grid",
            gridTemplateColumns: `repeat(${EVENTS.length}, 1fr)`,
            gap: 12,
          }}
        >
          {EVENTS.map((e) => (
            <div key={e.t} style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  background: e.color,
                  border: `3px solid #fff`,
                  boxShadow: `0 0 0 1px ${e.color}`,
                  marginBottom: 12,
                  position: "relative",
                  zIndex: 1,
                }}
              />
              <div
                style={{
                  fontFamily: "var(--fm)",
                  fontSize: 10,
                  color: C.stoneLt,
                  letterSpacing: ".06em",
                  textTransform: "uppercase",
                }}
              >
                T {e.t}
              </div>
              <div
                style={{
                  fontFamily: "var(--fd)",
                  fontSize: 16,
                  fontWeight: 500,
                  color: C.ink,
                  marginTop: 2,
                }}
              >
                {e.label}
              </div>
              <div style={{ fontSize: 12, color: C.stone, marginTop: 2 }}>{e.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <div
        style={{
          marginTop: 16,
          paddingTop: 14,
          borderTop: `1px solid ${C.ruleLt}`,
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
        }}
      >
        {[
          ["P1 за 30д", "1"],
          ["В рамках SLA", "100%"],
          ["MTTR avg", "38 мин"],
        ].map(([label, val]) => (
          <div key={label}>
            <div
              style={{
                fontFamily: "var(--fm)",
                fontSize: 10,
                letterSpacing: ".10em",
                textTransform: "uppercase",
                color: C.stone,
                marginBottom: 4,
              }}
            >
              {label}
            </div>
            <div
              style={{
                fontFamily: "var(--fd)",
                fontSize: 22,
                fontWeight: 500,
                color: C.forest,
                lineHeight: 1,
              }}
            >
              {val}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
