// Full-width "Grafana-screenshot" dashboard. Multiple panels in a typical SRE layout.
// Light theme to match light sections of landing.

const C = {
  ink: "#1a1815",
  inkLt: "#2c2a26",
  stone: "#78746a",
  stoneLt: "#a8a49c",
  rule: "rgba(26,24,21,.10)",
  ruleLt: "rgba(26,24,21,.05)",
  forest: "#1b4d3e",
  forestLt: "#2d6b58",
  forestDim: "rgba(27,77,62,.08)",
  amber: "#b45309",
  red: "#a13030",
  cream: "#f7f4ee",
  blue: "#34608c",
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

function StatPanel({ title, value, unit, sub, accent = C.forest }) {
  return (
    <div style={{ borderRight: `1px solid ${C.ruleLt}`, padding: "16px 18px" }}>
      <div
        style={{
          fontFamily: "var(--fm)",
          fontSize: 10,
          letterSpacing: ".10em",
          color: C.stoneLt,
          textTransform: "uppercase",
        }}
      >
        {title}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginTop: 6 }}>
        <span
          style={{
            fontFamily: "var(--fd)",
            fontSize: 28,
            fontWeight: 500,
            color: accent,
            letterSpacing: "-.02em",
            lineHeight: 1,
          }}
        >
          {value}
        </span>
        {unit && <span style={{ fontSize: 12, color: C.stoneLt }}>{unit}</span>}
      </div>
      <div style={{ fontFamily: "var(--fm)", fontSize: 10.5, color: C.stoneLt, marginTop: 4 }}>
        {sub}
      </div>
    </div>
  );
}

export default function DashboardWide() {
  // 24 hourly buckets
  const cpu = [22, 24, 26, 30, 35, 42, 48, 55, 60, 62, 65, 68, 70, 67, 64, 60, 55, 50, 45, 40, 38, 36, 34, 32];
  const ram = [55, 56, 58, 60, 62, 64, 66, 68, 70, 71, 72, 73, 74, 73, 72, 70, 68, 66, 65, 63, 62, 60, 58, 57];
  const reqs = [120, 140, 250, 480, 720, 980, 1240, 1480, 1620, 1700, 1800, 1900, 1950, 1820, 1640, 1410, 1180, 920, 680, 510, 380, 280, 210, 160];
  const errs = [0.01, 0.02, 0.02, 0.03, 0.04, 0.03, 0.05, 0.18, 0.42, 0.12, 0.05, 0.04, 0.03, 0.02, 0.03, 0.04, 0.03, 0.02, 0.02, 0.01, 0.01, 0.02, 0.01, 0.01];

  const W = 600;
  const H = 120;
  const Hsmall = 60;

  return (
    <div
      data-testid="dashboard-wide"
      style={{
        background: "#fff",
        border: `1px solid ${C.rule}`,
        borderRadius: 10,
        overflow: "hidden",
        boxShadow: "0 4px 32px rgba(26,24,21,.06)",
      }}
    >
      {/* Title bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 18px",
          background: C.cream,
          borderBottom: `1px solid ${C.rule}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: C.forest,
              boxShadow: `0 0 0 3px ${C.forestDim}`,
            }}
          />
          <span
            style={{
              fontFamily: "var(--fm)",
              fontSize: 11,
              color: C.ink,
              letterSpacing: ".05em",
            }}
          >
            client-llc / production · web-01 + 1c-01 + db-01
          </span>
        </div>
        <span style={{ fontFamily: "var(--fm)", fontSize: 10, color: C.stoneLt }}>
          last 24h · обновлено 12 с назад
        </span>
      </div>

      {/* 4 stat panels */}
      <div
        className="dash-stats"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          borderBottom: `1px solid ${C.ruleLt}`,
        }}
      >
        <StatPanel title="Uptime · 30 дней" value="99.97" unit="%" sub="2 окна обслуживания" />
        <StatPanel title="MTTR P1 · среднее" value="38" unit="мин" sub="цель ≤ 60 мин" />
        <StatPanel title="Активных алертов" value="0" sub="за последние 6 ч" />
        <StatPanel
          title="Backups · последние 24ч"
          value="14/14"
          accent={C.forest}
          sub="restic · AES-256 · облако"
        />
      </div>

      {/* Big chart panel */}
      <div style={{ padding: "16px 18px", borderBottom: `1px solid ${C.ruleLt}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
          <span
            style={{
              fontFamily: "var(--fm)",
              fontSize: 10,
              letterSpacing: ".10em",
              color: C.stoneLt,
              textTransform: "uppercase",
            }}
          >
            Requests / sec · web-01
          </span>
          <span style={{ fontFamily: "var(--fm)", fontSize: 11, color: C.stoneLt }}>
            <Dot color={C.forest} /> rps&nbsp;&nbsp;
            <Dot color={C.amber} /> 5xx %
          </span>
        </div>
        <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          {[0.25, 0.5, 0.75].map((g) => (
            <line key={g} x1="0" x2={W} y1={H * g} y2={H * g} stroke={C.ruleLt} strokeWidth="1" />
          ))}
          <path d={`${path(reqs, W, H)} L${W},${H} L0,${H} Z`} fill={C.forest} opacity="0.10" />
          <path d={path(reqs, W, H)} fill="none" stroke={C.forest} strokeWidth="1.6" />
          {/* Errors as small bars on top */}
          {errs.map((e, i) => {
            const w = W / errs.length - 1;
            const x = i * (W / errs.length);
            const barH = Math.min(H - 8, e * 200);
            return (
              <rect
                key={i}
                x={x}
                y={H - barH}
                width={w}
                height={barH}
                fill={e > 0.1 ? C.amber : "transparent"}
                opacity={e > 0.1 ? 0.7 : 0}
              />
            );
          })}
        </svg>
      </div>

      {/* Two side-by-side mini charts */}
      <div
        className="dash-mini"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          borderBottom: `1px solid ${C.ruleLt}`,
        }}
      >
        <div style={{ padding: "14px 18px", borderRight: `1px solid ${C.ruleLt}` }}>
          <div
            style={{
              fontFamily: "var(--fm)",
              fontSize: 10,
              letterSpacing: ".10em",
              color: C.stoneLt,
              textTransform: "uppercase",
              marginBottom: 6,
            }}
          >
            CPU · 1c-01 · текущее <span style={{ color: C.forest }}>· 32%</span>
          </div>
          <svg width="100%" height={Hsmall} viewBox={`0 0 ${W / 2} ${Hsmall}`} preserveAspectRatio="none">
            <path d={`${path(cpu, W / 2, Hsmall, 4, 4)} L${W / 2},${Hsmall} L0,${Hsmall} Z`} fill={C.forest} opacity="0.08" />
            <path d={path(cpu, W / 2, Hsmall, 4, 4)} fill="none" stroke={C.forest} strokeWidth="1.4" />
          </svg>
        </div>
        <div style={{ padding: "14px 18px" }}>
          <div
            style={{
              fontFamily: "var(--fm)",
              fontSize: 10,
              letterSpacing: ".10em",
              color: C.stoneLt,
              textTransform: "uppercase",
              marginBottom: 6,
            }}
          >
            RAM · 1c-01 · текущее <span style={{ color: C.amber }}>· 57%</span>
          </div>
          <svg width="100%" height={Hsmall} viewBox={`0 0 ${W / 2} ${Hsmall}`} preserveAspectRatio="none">
            <path d={`${path(ram, W / 2, Hsmall, 4, 4)} L${W / 2},${Hsmall} L0,${Hsmall} Z`} fill={C.amber} opacity="0.10" />
            <path d={path(ram, W / 2, Hsmall, 4, 4)} fill="none" stroke={C.amber} strokeWidth="1.4" />
          </svg>
        </div>
      </div>

      {/* Footer with hosts pill list */}
      <div
        style={{
          padding: "10px 18px",
          background: C.cream,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {[
            ["web-01", "ok"],
            ["1c-01", "ok"],
            ["db-01", "ok"],
            ["dc-01", "ok"],
            ["file-01", "ok"],
            ["mail-01", "ok"],
            ["ext-01", "warn"],
          ].map(([host, state]) => (
            <span
              key={host}
              style={{
                fontFamily: "var(--fm)",
                fontSize: 10,
                padding: "3px 8px",
                borderRadius: 3,
                color: state === "warn" ? C.amber : C.forest,
                background:
                  state === "warn" ? "rgba(180,83,9,.10)" : "rgba(27,77,62,.08)",
                border: `1px solid ${
                  state === "warn" ? "rgba(180,83,9,.20)" : "rgba(27,77,62,.16)"
                }`,
              }}
            >
              {host}
            </span>
          ))}
        </div>
        <span style={{ fontFamily: "var(--fm)", fontSize: 10, color: C.stoneLt }}>
          7 / 7 хостов up · 1 warn (диск 78%)
        </span>
      </div>

      <style>{`
        @media (max-width: 720px) {
          [data-testid="dashboard-wide"] .dash-stats { grid-template-columns: 1fr 1fr !important; }
          [data-testid="dashboard-wide"] .dash-mini { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}

function Dot({ color }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        borderRadius: "50%",
        background: color,
        marginRight: 4,
        verticalAlign: "middle",
      }}
    />
  );
}
