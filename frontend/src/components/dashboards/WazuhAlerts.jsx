// Wazuh / SIEM-style alerts table — Gold-tier feature.
// Dark theme, severity badges, clean monospace.

const C = {
  ink: "#0e0c0a",
  inkLt: "#1a1815",
  bg: "#181715",
  bgCard: "#1f1d1a",
  rule: "rgba(255,255,255,.08)",
  ruleLt: "rgba(255,255,255,.04)",
  stone: "#9c9890",
  stoneLt: "#787570",
  red: "#e7625f",
  amber: "#e8b75f",
  forest: "#5fc9a2",
  blue: "#5ea7ea",
};

const SEVERITY = {
  high: { color: C.red, bg: "rgba(231,98,95,.15)", label: "HIGH" },
  med: { color: C.amber, bg: "rgba(232,183,95,.15)", label: "MED" },
  low: { color: C.blue, bg: "rgba(94,167,234,.12)", label: "LOW" },
  info: { color: C.stoneLt, bg: "rgba(255,255,255,.04)", label: "INFO" },
};

const ROWS = [
  {
    sev: "high",
    rule: "5710 · sshd brute-force",
    host: "ext.client-llc",
    src: "203.0.113.42",
    when: "03:18",
  },
  {
    sev: "med",
    rule: "60106 · GPO change · admins",
    host: "dc-01.corp",
    src: "10.9.0.21",
    when: "02:55",
  },
  {
    sev: "high",
    rule: "31100 · suspicious PowerShell",
    host: "win-01.corp",
    src: "10.9.0.78",
    when: "02:41",
  },
  {
    sev: "low",
    rule: "5402 · sudo by user",
    host: "1c-01.corp",
    src: "10.9.0.15",
    when: "02:30",
  },
  {
    sev: "info",
    rule: "550 · file integrity OK",
    host: "file-01.corp",
    src: "—",
    when: "02:00",
  },
];

function Badge({ sev }) {
  const s = SEVERITY[sev];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 8px",
        background: s.bg,
        color: s.color,
        fontFamily: "var(--fm)",
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: ".06em",
        borderRadius: 3,
        textTransform: "uppercase",
      }}
    >
      {s.label}
    </span>
  );
}

export default function WazuhAlerts() {
  return (
    <div
      data-testid="wazuh-alerts"
      style={{
        background: C.bg,
        border: `1px solid ${C.rule}`,
        borderRadius: 8,
        overflow: "hidden",
        color: "#fff",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 18px",
          background: C.inkLt,
          borderBottom: `1px solid ${C.rule}`,
        }}
      >
        <div>
          <div
            style={{
              fontFamily: "var(--fm)",
              fontSize: 10,
              letterSpacing: ".10em",
              color: C.stoneLt,
              textTransform: "uppercase",
            }}
          >
            Wazuh · security events · последний час
          </div>
          <div
            style={{
              fontFamily: "var(--fd)",
              fontSize: 22,
              fontWeight: 500,
              marginTop: 2,
            }}
          >
            <span style={{ color: C.red }}>2</span>{" "}
            <span style={{ color: C.stoneLt, fontSize: 14 }}>HIGH</span>{" "}
            <span style={{ color: C.amber }}>1</span>{" "}
            <span style={{ color: C.stoneLt, fontSize: 14 }}>MED</span>
          </div>
        </div>
        <span
          style={{
            padding: "6px 12px",
            background: "rgba(95,201,162,.10)",
            border: `1px solid rgba(95,201,162,.30)`,
            borderRadius: 4,
            fontFamily: "var(--fm)",
            fontSize: 10,
            color: C.forest,
            letterSpacing: ".06em",
            textTransform: "uppercase",
          }}
        >
          Gold tier
        </span>
      </div>

      {/* Table */}
      <div style={{ padding: "8px 0" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "70px 1fr 130px 110px 50px",
            gap: 12,
            padding: "8px 18px",
            fontFamily: "var(--fm)",
            fontSize: 9.5,
            letterSpacing: ".10em",
            color: C.stoneLt,
            textTransform: "uppercase",
            borderBottom: `1px solid ${C.ruleLt}`,
          }}
        >
          <span>Severity</span>
          <span>Rule</span>
          <span>Host</span>
          <span>Source IP</span>
          <span style={{ textAlign: "right" }}>UTC</span>
        </div>
        {ROWS.map((r, i) => (
          <div
            key={i}
            style={{
              display: "grid",
              gridTemplateColumns: "70px 1fr 130px 110px 50px",
              gap: 12,
              padding: "10px 18px",
              alignItems: "center",
              borderBottom: i < ROWS.length - 1 ? `1px solid ${C.ruleLt}` : "none",
              fontFamily: "var(--fm)",
              fontSize: 12,
              color: "#e3dfd6",
            }}
          >
            <span>
              <Badge sev={r.sev} />
            </span>
            <span style={{ color: "#f1ede4", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {r.rule}
            </span>
            <span style={{ color: C.stone, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {r.host}
            </span>
            <span style={{ color: C.stoneLt, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {r.src}
            </span>
            <span style={{ color: C.stoneLt, textAlign: "right" }}>{r.when}</span>
          </div>
        ))}
      </div>

      <div
        style={{
          padding: "10px 18px",
          background: C.inkLt,
          borderTop: `1px solid ${C.rule}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontFamily: "var(--fm)",
          fontSize: 11,
          color: C.stoneLt,
        }}
      >
        <span>
          ssh-bruteforce · IP <span style={{ color: C.red }}>203.0.113.42</span> заблокирован активным реагированием через 90 с
        </span>
        <span>view all →</span>
      </div>
    </div>
  );
}
