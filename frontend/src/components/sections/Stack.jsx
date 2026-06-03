import { OssIcon, OSS_TOOLS, RuIcon, RU_TOOLS, ServiceIcon, SERVICE_LIST } from "@/components/icons";

function IconFor({ kind, name, size = 28 }) {
  if (kind === "oss") return <OssIcon name={name} size={size} />;
  if (kind === "ru") return <RuIcon name={name} size={size} />;
  return <ServiceIcon name={name} size={size} />;
}

function Tile({ kind, name, label }) {
  return (
    <div
      data-testid={`stack-tile-${name}`}
      className="stack-tile"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "flex-start",
        gap: 14,
        padding: "20px 12px 18px",
        background: "#fff",
        border: "1px solid var(--rule-lt)",
        borderRadius: 10,
        transition: "border-color .15s ease, transform .15s ease, box-shadow .15s ease",
        cursor: "default",
        minHeight: 108,
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--ink)",
        }}
      >
        <IconFor kind={kind} name={name} size={32} />
      </div>
      <div
        style={{
          fontFamily: "var(--fb)",
          fontWeight: 500,
          fontSize: 12.5,
          lineHeight: 1.3,
          color: "var(--ink)",
          textAlign: "center",
          letterSpacing: "-.005em",
          maxWidth: "100%",
          wordBreak: "normal",
          overflowWrap: "break-word",
          hyphens: "auto",
        }}
      >
        {label}
      </div>
    </div>
  );
}

const WHAT_WE_ADMIN = [
  { name: "windows", label: "Windows Server" },
  { name: "linux", label: "Linux" },
  { name: "astra", label: "Astra Linux" },
  { name: "ad", label: "Active Directory" },
  { name: "onec", label: "1С" },
  { name: "mail", label: "Почта" },
  { name: "dns", label: "DNS" },
  { name: "fileserver", label: "Файловые шары" },
  { name: "database", label: "PostgreSQL · MS SQL" },
  { name: "web", label: "Сайт · API" },
  { name: "shield-lock", label: "Защищённый канал" },
  { name: "more", label: "И другие" },
];

const HOW_WE_ADMIN = [
  { kind: "oss", name: "linux", label: "Linux" },
  { kind: "ru", name: "postgrespro", label: "Postgres Pro" },
  { kind: "oss", name: "prometheus", label: "Prometheus" },
  { kind: "oss", name: "grafana", label: "Grafana" },
  { kind: "oss", name: "wazuh", label: "Wazuh" },
  { kind: "ru", name: "kaspersky", label: "Kaspersky" },
  { kind: "service", name: "cloud", label: "Облако" },
  { kind: "oss", name: "ansible", label: "Ansible" },
  { kind: "service", name: "telegram", label: "Telegram" },
  { kind: "ru", name: "max", label: "MAX" },
  { kind: "service", name: "more", label: "И другие" },
];

function MixedRow({ title, items }) {
  return (
    <div data-testid="stack-row-mixed" style={{ marginBottom: 0 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 20,
        }}
      >
        <span className="tag-dot" style={{ color: "var(--ink)" }}>
          {title}
        </span>
      </div>
      <div
        className="stack-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
          gap: 12,
        }}
      >
        {items.map((it) => (
          <Tile key={`${it.kind}-${it.name}`} kind={it.kind} name={it.name} label={it.label} />
        ))}
      </div>
    </div>
  );
}

export default function Stack() {
  return (
    <section
      data-testid="stack-section"
      id="stack"
      style={{ padding: "120px 0", background: "var(--cream)" }}
    >
      <div className="wrap">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) minmax(0, 460px)",
            gap: 64,
            alignItems: "end",
            marginBottom: 56,
            paddingBottom: 32,
            borderBottom: "1px solid var(--rule)",
          }}
          className="stack-header-grid"
        >
          <div>
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              Стек
            </div>
            <h2 className="h-section">
              Что мы <em>обслуживаем</em>
              <br />
              и <em>чем</em> обслуживаем.
            </h2>
          </div>
          <p className="section-lead" style={{ maxWidth: 460 }}>
            Сверху — что у клиента под админкой. Снизу — наш собственный
            инструментарий: open source и российское ПО из реестра Минцифры
            для соответствия 152-ФЗ.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 48 }}>
          <MixedRow
            title="Что обслуживаем"
            items={WHAT_WE_ADMIN.map((it) => ({ kind: "service", ...it }))}
          />
          <MixedRow title="Чем обслуживаем" items={HOW_WE_ADMIN} />
        </div>

        <p
          style={{
            marginTop: 40,
            fontSize: 12,
            color: "var(--stone-lt)",
            textAlign: "center",
            fontFamily: "var(--fm)",
            letterSpacing: ".04em",
          }}
        >
          Конкретный набор зависит от тарифа
        </p>
      </div>

      <style>{`
        [data-testid="stack-section"] .stack-tile:hover {
          border-color: var(--rule);
          transform: translateY(-1px);
          box-shadow: 0 1px 2px rgba(0,0,0,.03);
        }
        @media (max-width: 720px) {
          [data-testid="stack-section"] .stack-header-grid {
            grid-template-columns: 1fr !important;
            gap: 24px !important;
          }
          [data-testid="stack-section"] .stack-grid {
            grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)) !important;
            gap: 10px !important;
          }
        }
      `}</style>
    </section>
  );
}
