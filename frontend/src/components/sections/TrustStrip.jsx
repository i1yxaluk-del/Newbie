import { OssIcon, RuIcon } from "@/components/icons";

// Mixed strip — short row of well-known marks (RU + OSS together) to anchor trust.
const ROW = [
  { kind: "ru", name: "astra", label: "Astra Linux" },
  { kind: "oss", name: "linux", label: "Linux" },
  { kind: "ru", name: "postgrespro", label: "Postgres Pro" },
  { kind: "oss", name: "prometheus", label: "Prometheus" },
  { kind: "oss", name: "grafana", label: "Grafana" },
  { kind: "ru", name: "yandex", label: "Yandex Cloud" },
  { kind: "oss", name: "ansible", label: "Ansible" },
  { kind: "oss", name: "wazuh", label: "Wazuh" },
  { kind: "ru", name: "kaspersky", label: "Kaspersky" },
  { kind: "ru", name: "onec", label: "1С" },
  { kind: "oss", name: "wireguard", label: "WireGuard" },
  { kind: "oss", name: "docker", label: "Docker" },
];

export default function TrustStrip() {
  return (
    <section
      data-testid="trust-strip"
      style={{
        padding: "56px 0",
        background: "var(--cream)",
        borderTop: "1px solid var(--rule-lt)",
        borderBottom: "1px solid var(--rule-lt)",
      }}
    >
      <div className="wrap">
        <div
          className="tag-dot"
          style={{ marginBottom: 24, justifyContent: "center", display: "flex" }}
        >
          Стек: открытое ПО + РФ ПО (реестр Минцифры)
        </div>
        <div
          className="trust-strip-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(12, minmax(0, 1fr))",
            gap: 16,
            alignItems: "center",
          }}
        >
          {ROW.map((it) => (
            <div
              key={it.label}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 6,
                color: "var(--stone)",
                opacity: 0.85,
              }}
            >
              <div style={{ height: 28, display: "flex", alignItems: "center" }}>
                {it.kind === "oss" ? (
                  <OssIcon name={it.name} size={28} />
                ) : (
                  <RuIcon name={it.name} size={28} />
                )}
              </div>
              <div
                style={{
                  fontFamily: "var(--fm)",
                  fontSize: 10,
                  color: "var(--stone-lt)",
                  letterSpacing: ".05em",
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
      <style>{`
        @media (max-width: 960px) {
          .trust-strip-grid { grid-template-columns: repeat(6, minmax(0, 1fr)) !important; gap: 24px 12px !important; }
        }
        @media (max-width: 480px) {
          .trust-strip-grid { grid-template-columns: repeat(4, minmax(0, 1fr)) !important; }
        }
      `}</style>
    </section>
  );
}
