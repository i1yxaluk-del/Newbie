// Single big chart with p50 / p95 / p99 lines — for "Видим" pillar.
// Below: 4-row log preview to suggest "metrics + logs" coverage.

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

function path(values, w, h, padT = 6, padB = 6) {
  if (!values?.length) return "";
  const maxV = Math.max(...values);
  const minV = Math.min(...values);
  const range = maxV - minV || 1;
  const step = w / Math.max(1, values.length - 1);
  return values
    .map((v, i) => {
      const x = i * step;
      const y = padT + (h - padT - padB) * (1 - (v - minV) / range);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

const LOGS = [
  { t: "12:04:18", lvl: "info", host: "web-01", msg: "GET /api/health 200 12ms" },
  { t: "12:04:17", lvl: "warn", host: "db-01", msg: "slow query 1.2s SELECT … FROM leads" },
  { t: "12:04:16", lvl: "info", host: "1c-01", msg: "scheduled task completed" },
  { t: "12:04:15", lvl: "info", host: "file-01", msg: "smb session opened user=ivanov" },
];

function Legend({ dot, label }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, color: C.stone }}>
      <span
        style={{ width: 8, height: 8, borderRadius: "50%", background: dot, display: "inline-block" }}
      />
      {label}
    </span>
  );
}

export default function LatencyChart() {
  const p50 = [42, 40, 45, 48, 50, 52, 55, 58, 60, 62, 60, 58, 55, 52, 48, 45, 42, 40, 38, 40, 42, 45, 50, 48];
  const p95 = [120, 115, 130, 145, 160, 175, 190, 210, 220, 225, 215, 200, 180, 165, 150, 140, 130, 120, 115, 122, 130, 145, 160, 152];
  const p99 = [280, 270, 295, 320, 360, 410, 450, 490, 510, 525, 510, 480, 440, 410, 370, 340, 310, 285, 270, 280, 295, 320, 360, 340];

  const W = 480;
  const H = 160;

  return (
    <div
      data-testid="latency-chart"
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
          marginBottom: 14,
          paddingBottom: 12,
          borderBottom: `1px solid ${C.ruleLt}`,
          flexWrap: "wrap",
          gap: 12,
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
            HTTP latency · последние 24 ч
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
            web-01 · все эндпоинты
          </div>
        </div>
        <div style={{ display: "flex", gap: 14, fontFamily: "var(--fm)", fontSize: 11 }}>
          <Legend dot={C.stoneLt} label="p50 48ms" />
          <Legend dot={C.forestLt} label="p95 152ms" />
          <Legend dot={C.forest} label="p99 340ms" />
        </div>
      </div>

      <svg
        width="100%"
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        style={{ display: "block" }}
      >
        {[0.25, 0.5, 0.75].map((g) => (
          <line key={g} x1="0" x2={W} y1={H * g} y2={H * g} stroke={C.ruleLt} strokeWidth="1" />
        ))}
        <path d={`${path(p99, W, H)} L${W},${H} L0,${H} Z`} fill={C.forest} opacity="0.06" />
        <path d={path(p50, W, H)} fill="none" stroke={C.stoneLt} strokeWidth="1.4" />
        <path d={path(p95, W, H)} fill="none" stroke={C.forestLt} strokeWidth="1.6" />
        <path d={path(p99, W, H)} fill="none" stroke={C.forest} strokeWidth="1.8" />
      </svg>

      <div style={{ marginTop: 16, paddingTop: 14, borderTop: `1px solid ${C.ruleLt}` }}>
        <div
          style={{
            fontFamily: "var(--fm)",
            fontSize: 10,
            letterSpacing: ".10em",
            textTransform: "uppercase",
            color: C.stone,
            marginBottom: 8,
          }}
        >
          Loki · последние логи
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {LOGS.map((l) => (
            <div
              key={l.t + l.host}
              style={{
                display: "grid",
                gridTemplateColumns: "76px 56px 64px 1fr",
                gap: 10,
                fontFamily: "var(--fm)",
                fontSize: 11.5,
                color: C.stone,
                padding: "3px 0",
              }}
            >
              <span style={{ color: C.stoneLt }}>{l.t}</span>
              <span
                style={{
                  color: l.lvl === "warn" ? C.amber : C.forest,
                  textTransform: "uppercase",
                  fontWeight: 600,
                  fontSize: 10,
                  letterSpacing: ".08em",
                }}
              >
                {l.lvl}
              </span>
              <span style={{ color: C.ink }}>{l.host}</span>
              <span
                style={{
                  color: C.stone,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {l.msg}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
