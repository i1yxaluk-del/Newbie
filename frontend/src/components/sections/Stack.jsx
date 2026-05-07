import { OssIcon, OSS_TOOLS, RuIcon, RU_TOOLS } from "@/components/icons";

function Column({ title, tag, items, kind }) {
  const Icon = kind === "oss" ? OssIcon : RuIcon;
  return (
    <div
      data-testid={`stack-column-${kind}`}
      style={{
        background: "#fff",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: "32px 28px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
          paddingBottom: 16,
          borderBottom: "1px solid var(--rule-lt)",
        }}
      >
        <h3
          className="font-display"
          style={{
            fontSize: 24,
            fontWeight: 500,
            color: "var(--ink)",
            margin: 0,
            letterSpacing: "-.01em",
          }}
        >
          {title}
        </h3>
        <span
          className="tag-dot"
          style={{ color: kind === "oss" ? "var(--forest)" : "var(--stone)" }}
        >
          {tag}
        </span>
      </div>

      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 14 }}>
        {items.map((it) => (
          <li
            key={it.name}
            style={{
              display: "grid",
              gridTemplateColumns: "32px 1fr",
              gap: 14,
              alignItems: "start",
              padding: "10px 0",
              borderTop: "1px solid var(--rule-lt)",
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--ink)",
              }}
            >
              <Icon name={it.name} size={28} />
            </div>
            <div>
              <div
                style={{
                  fontFamily: "var(--fb)",
                  fontWeight: 500,
                  fontSize: 15,
                  color: "var(--ink)",
                  letterSpacing: "-.01em",
                }}
              >
                {it.label}
              </div>
              <div style={{ fontSize: 13, color: "var(--stone)", lineHeight: 1.5, marginTop: 2 }}>
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
              Технологии
            </div>
            <h2 className="h-section">
              Открытое ПО плюс <em>российский реестр.</em>
              <br />
              Без vendor lock-in.
            </h2>
          </div>
          <p className="section-lead" style={{ maxWidth: 460 }}>
            Только проверенные временем инструменты. Открытый код, чтобы вы могли
            забрать стек целиком и привезти к другому подрядчику. Российские
            продукты из реестра Минцифры — для 152-ФЗ и приказа Минцифры №486.
          </p>
        </div>

        <div
          className="stack-cols"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 32,
            alignItems: "stretch",
          }}
        >
          <Column
            title="Открытое ПО"
            tag="Open source"
            kind="oss"
            items={OSS_TOOLS}
          />
          <Column
            title="РФ ПО"
            tag="Реестр Минцифры"
            kind="ru"
            items={RU_TOOLS}
          />
        </div>

        <p
          style={{
            marginTop: 32,
            fontSize: 13,
            color: "var(--stone-lt)",
            textAlign: "center",
            fontFamily: "var(--fm)",
            letterSpacing: ".04em",
          }}
        >
          Конкретный набор зависит от тарифа. Полный перечень — в JUNIOR_GUIDE.
        </p>
      </div>

      <style>{`
        @media (max-width: 960px) {
          .stack-header-grid { grid-template-columns: 1fr !important; gap: 24px !important; }
          .stack-cols { grid-template-columns: 1fr !important; gap: 20px !important; }
        }
      `}</style>
    </section>
  );
}
