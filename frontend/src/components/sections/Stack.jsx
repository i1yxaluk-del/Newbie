import { OssIcon, OSS_TOOLS, RuIcon, RU_TOOLS, ServiceIcon, SERVICE_LIST } from "@/components/icons";

function IconFor({ kind, name, size = 28 }) {
  if (kind === "oss") return <OssIcon name={name} size={size} />;
  if (kind === "ru") return <RuIcon name={name} size={size} />;
  return <ServiceIcon name={name} size={size} />;
}

function Column({ title, tag, items, kind, accent = "var(--forest)" }) {
  return (
    <div
      data-testid={`stack-column-${kind}`}
      style={{
        background: "#fff",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: "28px 24px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 20,
          paddingBottom: 14,
          borderBottom: "1px solid var(--rule-lt)",
        }}
      >
        <h3
          className="font-display"
          style={{
            fontSize: 22,
            fontWeight: 500,
            color: "var(--ink)",
            margin: 0,
            letterSpacing: "-.01em",
          }}
        >
          {title}
        </h3>
        <span className="tag-dot" style={{ color: accent }}>
          {tag}
        </span>
      </div>

      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 0 }}>
        {items.map((it, i) => (
          <li
            key={it.name}
            style={{
              display: "grid",
              gridTemplateColumns: "28px 1fr",
              gap: 14,
              alignItems: "start",
              padding: "12px 0",
              borderTop: i === 0 ? "none" : "1px solid var(--rule-lt)",
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--ink)",
                marginTop: 1,
              }}
            >
              <IconFor kind={kind} name={it.name} size={24} />
            </div>
            <div>
              <div
                style={{
                  fontFamily: "var(--fb)",
                  fontWeight: 500,
                  fontSize: 14,
                  color: "var(--ink)",
                  letterSpacing: "-.01em",
                }}
              >
                {it.label}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--stone)", lineHeight: 1.45, marginTop: 2 }}>
                {it.desc}
              </div>
            </div>
          </li>
        ))}
      </ul>
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
            Слева — сервисы клиента. Справа — наши инструменты: открытый код
            и РФ-реестр для соответствия 152-ФЗ.
          </p>
        </div>

        <div
          className="stack-cols"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 24,
            alignItems: "stretch",
          }}
        >
          <Column
            title="Сервисы клиента"
            tag="Что админим"
            kind="service"
            items={SERVICE_LIST}
            accent="var(--ink)"
          />
          <Column
            title="Open source"
            tag="Чем админим"
            kind="oss"
            items={OSS_TOOLS}
            accent="var(--forest)"
          />
          <Column
            title="Реестр Минцифры"
            tag="РФ ПО"
            kind="ru"
            items={RU_TOOLS}
            accent="var(--stone)"
          />
        </div>

        <p
          style={{
            marginTop: 28,
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
        @media (max-width: 1080px) {
          [data-testid="stack-section"] .stack-cols { grid-template-columns: 1fr 1fr !important; }
        }
        @media (max-width: 720px) {
          [data-testid="stack-section"] .stack-header-grid { grid-template-columns: 1fr !important; gap: 24px !important; }
          [data-testid="stack-section"] .stack-cols { grid-template-columns: 1fr !important; gap: 16px !important; }
        }
      `}</style>
    </section>
  );
}
