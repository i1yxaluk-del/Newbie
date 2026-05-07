// Golden Signals dashboard preview — 4-up grid in Antimetal style.
// Inspired by Google SRE book: Latency, Traffic, Errors, Saturation.
// All inline SVG, no dependencies. Forest accent on cream surface.

const COLORS = {
  ink: "#1a1815",
  stone: "#78746a",
  stoneLt: "#a8a49c",
  rule: "rgba(26,24,21,.10)",
  ruleLt: "rgba(26,24,21,.05)",
  forest: "#1b4d3e",
  forestDim: "rgba(27,77,62,.10)",
  amber: "#b45309",
};

function sparklinePath(values, w, h, padTop = 4, padBottom = 4) {
  if (!values?.length) return "";
  const maxV = Math.max(...values, 0.001);
  const step = w / Math.max(1, values.length - 1);
  return values
    .map((v, i) => {
      const x = i * step;
      const y = padTop + (h - padTop - padBottom) * (1 - v / maxV);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function areaPath(values, w, h, padTop = 4, padBottom = 4) {
  const line = sparklinePath(values, w, h, padTop, padBottom);
  return `${line} L${w},${h - padBottom} L0,${h - padBottom} Z`;
}

function Tile({ title, value, unit, trend, children }) {
  return (
    <div
      style={{
        border: `1px solid ${COLORS.rule}`,
        borderRadius: 6,
        padding: "16px 16px 12px",
        background: "#fff",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        minHeight: 130,
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span
          style={{
            fontFamily: "var(--fm)",
            fontSize: 10,
            letterSpacing: ".10em",
            textTransform: "uppercase",
            color: COLORS.stone,
          }}
        >
          {title}
        </span>
        {trend && (
          <span
            style={{
              fontFamily: "var(--fm)",
              fontSize: 10,
              color: trend.startsWith("-") ? COLORS.forest : COLORS.amber,
            }}
          >
            {trend}
          </span>
        )}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span
          style={{
            fontFamily: "var(--fd)",
            fontSize: 28,
            fontWeight: 500,
            color: COLORS.ink,
            lineHeight: 1,
            letterSpacing: "-.02em",
          }}
        >
          {value}
        </span>
        {unit && <span style={{ fontSize: 12, color: COLORS.stoneLt }}>{unit}</span>}
      </div>
      <div style={{ marginTop: "auto" }}>{children}</div>
    </div>
  );
}

export default function GoldenSignals({ compact = false }) {
  const latency = [220, 215, 230, 210, 198, 205, 192, 187, 180, 187];
  const traffic = [420, 510, 690, 890, 1100, 1240, 1247, 1180, 1090, 980, 870, 720];
  const errors = [0.02, 0.03, 0.02, 0.04, 0.18, 0.08, 0.04, 0.04];
  const saturation = 0.62;

  const w = 200;
  const h = 44;

  return (
    <div
      data-testid="golden-signals"
      style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
    >
      <Tile title="Latency · p95" value="187" unit="ms" trend="-12%">
        <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
          <path d={areaPath(latency.map((x) => 1 / x), w, h, 6, 4)} fill={COLORS.forestDim} />
          <path
            d={sparklinePath(latency.map((x) => 1 / x), w, h, 6, 4)}
            fill="none"
            stroke={COLORS.forest}
            strokeWidth="1.5"
          />
        </svg>
      </Tile>

      <Tile title="Traffic" value="1 247" unit="r/s" trend="+8%">
        <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
          <path d={areaPath(traffic, w, h, 6, 4)} fill={COLORS.forestDim} />
          <path
            d={sparklinePath(traffic, w, h, 6, 4)}
            fill="none"
            stroke={COLORS.forest}
            strokeWidth="1.5"
          />
        </svg>
      </Tile>

      <Tile title="Errors · 5xx" value="0.04" unit="%" trend="-22%">
        <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
          {errors.map((e, i) => {
            const barW = w / errors.length - 4;
            const x = i * (w / errors.length) + 2;
            const barH = Math.max(2, (e / 0.2) * (h - 8));
            return (
              <rect
                key={i}
                x={x}
                y={h - 4 - barH}
                width={barW}
                height={barH}
                fill={e > 0.1 ? COLORS.amber : COLORS.forest}
                opacity={e > 0.1 ? 0.85 : 0.6}
              />
            );
          })}
        </svg>
      </Tile>

      <Tile title="Saturation · CPU" value="62" unit="%">
        <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
          <rect x="0" y={h / 2 - 4} width={w} height="8" rx="4" fill={COLORS.ruleLt} />
          <rect
            x="0"
            y={h / 2 - 4}
            width={w * saturation}
            height="8"
            rx="4"
            fill={COLORS.forest}
          />
          <line
            x1={w * 0.85}
            x2={w * 0.85}
            y1={h / 2 - 8}
            y2={h / 2 + 8}
            stroke={COLORS.amber}
            strokeWidth="1.5"
            strokeDasharray="2 2"
          />
        </svg>
      </Tile>

      {!compact && (
        <div
          style={{
            gridColumn: "1 / -1",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "10px 14px",
            border: `1px solid ${COLORS.rule}`,
            borderRadius: 6,
            background: COLORS.forestDim,
            fontSize: 12,
            color: COLORS.forest,
          }}
        >
          <span style={{ fontWeight: 500 }}>4 / 4 серверов · все UP · последние 24 ч</span>
          <span style={{ fontFamily: "var(--fm)", fontSize: 11 }}>обновлено 23 с назад</span>
        </div>
      )}
    </div>
  );
}
