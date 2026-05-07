import { OssIcon, RuIcon, ServiceIcon } from "@/components/icons";

// Two rows: "что админим" (services) + "чем админим" (tools, RU+OSS mix).
const SERVICES_ROW = [
  { kind: "service", name: "windows", label: "Windows Server" },
  { kind: "service", name: "ad", label: "Active Directory" },
  { kind: "service", name: "onec", label: "1С" },
  { kind: "service", name: "mail", label: "Почта · DNS" },
  { kind: "service", name: "fileserver", label: "Файловые шары" },
  { kind: "service", name: "database", label: "PostgreSQL · MS SQL" },
  { kind: "service", name: "web", label: "Сайт · API" },
  { kind: "service", name: "vpn", label: "VPN · периметр" },
];

const TOOLS_ROW = [
  { kind: "ru", name: "astra", label: "Astra" },
  { kind: "oss", name: "linux", label: "Linux" },
  { kind: "ru", name: "postgrespro", label: "Postgres Pro" },
  { kind: "oss", name: "prometheus", label: "Prometheus" },
  { kind: "oss", name: "grafana", label: "Grafana" },
  { kind: "oss", name: "wazuh", label: "Wazuh" },
  { kind: "ru", name: "kaspersky", label: "Kaspersky" },
  { kind: "ru", name: "yandex", label: "Yandex Cloud" },
  { kind: "oss", name: "ansible", label: "Ansible" },
  { kind: "oss", name: "wireguard", label: "WireGuard" },
];

function iconFor({ kind, name }) {
  if (kind === "oss") return <OssIcon name={name} size={28} />;
  if (kind === "ru") return <RuIcon name={name} size={28} />;
  return <ServiceIcon name={name} size={28} />;
}

function Row({ label, items, gridCols }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div
        className="tag-dot"
        style={{
          marginBottom: 18,
          justifyContent: "center",
          display: "flex",
        }}
      >
        {label}
      </div>
      <div
        className="trust-strip-grid"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${gridCols}, minmax(0, 1fr))`,
          gap: 16,
          alignItems: "center",
        }}
      >
        {items.map((it) => (
          <div
            key={it.label}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              color: "var(--stone)",
              opacity: 0.9,
            }}
          >
            <div style={{ height: 28, display: "flex", alignItems: "center" }}>
              {iconFor(it)}
            </div>
            <div
              style={{
                fontFamily: "var(--fm)",
                fontSize: 10,
                color: "var(--stone-lt)",
                letterSpacing: ".04em",
                textAlign: "center",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                maxWidth: "100%",
              }}
            >
              {it.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TrustStrip() {
  return (
    <section
      data-testid="trust-strip"
      style={{
        padding: "64px 0 48px",
        background: "var(--cream)",
        borderTop: "1px solid var(--rule-lt)",
        borderBottom: "1px solid var(--rule-lt)",
      }}
    >
      <div className="wrap">
        <Row
          label="Что обслуживаем"
          items={SERVICES_ROW}
          gridCols={SERVICES_ROW.length}
        />
        <Row
          label="Чем обслуживаем · open source + РФ реестр"
          items={TOOLS_ROW}
          gridCols={TOOLS_ROW.length}
        />
      </div>
      <style>{`
        @media (max-width: 1080px) {
          [data-testid="trust-strip"] .trust-strip-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
            gap: 24px 12px !important;
          }
        }
        @media (max-width: 720px) {
          [data-testid="trust-strip"] .trust-strip-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
          }
        }
        @media (max-width: 480px) {
          [data-testid="trust-strip"] .trust-strip-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
          }
        }
      `}</style>
    </section>
  );
}
