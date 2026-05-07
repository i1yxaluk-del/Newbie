// Backup health dashboard for "Сохраняем" pillar.

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

const DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

const MATRIX = [
  { host: "web-01", days: ["ok", "ok", "ok", "ok", "ok", "ok", "ok"], size: "1.2 ГБ" },
  { host: "1c-01", days: ["ok", "ok", "ok", "ok", "warn", "ok", "ok"], size: "8.4 ГБ" },
  { host: "db-01", days: ["ok", "ok", "ok", "ok", "ok", "ok", "ok"], size: "5.2 ГБ" },
  { host: "file-01", days: ["ok", "ok", "ok", "ok", "ok", "ok", "ok"], size: "12.8 ГБ" },
];

const COLOR = {
  ok: C.forest,
  warn: C.amber,
  fail: "#a13030",
};

function Row({ row }) {
  return (
    <>
      <div style={{ fontFamily: "var(--fm)", fontSize: 12, color: C.ink }}>{row.host}</div>
      {row.days.map((s, i) => (
        <div
          key={i}
          title={s === "ok" ? "OK" : s === "warn" ? "verify pending" : "FAIL"}
          style={{
            height: 28,
            borderRadius: 3,
            background: COLOR[s],
            opacity: s === "ok" ? 0.85 : 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontFamily: "var(--fm)",
            fontSize: 10,
          }}
        >
          {s === "warn" ? "…" : ""}
        </div>
      ))}
      <div
        style={{
          fontFamily: "var(--fm)",
          fontSize: 11,
          color: C.stoneLt,
          textAlign: "right",
        }}
      >
        {row.size}
      </div>
    </>
  );
}

export default function BackupHealth() {
  return (
    <div
      data-testid="backup-health"
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
            Restic · последние 7 дней
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
            27 / 28 ✓ <span style={{ fontSize: 14, color: C.stoneLt }}>· 1 verify-pending</span>
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
          AES-256 · облачное хранилище
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "84px repeat(7, 1fr) 70px",
          gap: 6,
          alignItems: "center",
        }}
      >
        <div />
        {DAYS.map((d) => (
          <div
            key={d}
            style={{
              fontFamily: "var(--fm)",
              fontSize: 10,
              color: C.stoneLt,
              letterSpacing: ".06em",
              textAlign: "center",
              textTransform: "uppercase",
            }}
          >
            {d}
          </div>
        ))}
        <div />
        {MATRIX.map((row) => (
          <Row key={row.host} row={row} />
        ))}
      </div>

      <div
        style={{
          marginTop: 18,
          padding: "12px 14px",
          background: "rgba(27,77,62,.04)",
          border: `1px solid ${C.ruleLt}`,
          borderRadius: 6,
          fontSize: 13,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          color: C.stone,
          flexWrap: "wrap",
          gap: 6,
        }}
      >
        <span>
          Последний restore-test: <span style={{ color: C.forest, fontWeight: 500 }}>2 ч назад</span> · db-01 · 5.2 ГБ ·{" "}
          <span style={{ color: C.forest, fontWeight: 500 }}>OK</span>
        </span>
        <span style={{ fontFamily: "var(--fm)", fontSize: 11, color: C.stoneLt }}>03:47 MSK</span>
      </div>
    </div>
  );
}
