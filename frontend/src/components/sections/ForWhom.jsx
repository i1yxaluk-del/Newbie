import { Briefcase, Stethoscope, Factory } from "lucide-react";

const SEGMENTS = [
  {
    Icon: Briefcase,
    tag: "Сегмент A",
    title: "Юристы, бухгалтеры, консалтинг",
    size: "15–80 человек",
    pain: "1С + файловый сервер + «приходящий сисадмин». Падение 1С = остановка всей компании.",
    outcome: "Bronze или Silver: мониторинг + бэкапы + SLA. Фиксированная плата 20–50k ₽/мес вместо штатного сисадмина.",
    plan: "Bronze · Silver",
  },
  {
    Icon: Stethoscope,
    tag: "Сегмент B",
    title: "Медклиники, стоматологии, лаборатории",
    size: "10–150 рабочих мест",
    pain: "МИС + ПДн пациентов + проверки Роспотребнадзора / Росздравнадзора. Риск штрафов по 152-ФЗ.",
    outcome: "Gold: Wazuh SIEM, Kaspersky, документированный доступ, отчёты для проверяющих. 70–120k ₽/мес.",
    plan: "Gold",
  },
  {
    Icon: Factory,
    tag: "Сегмент C",
    title: "Производство, логистика, торговля",
    size: "80–300 сотрудников · 2–3 IT-специалиста",
    pain: "Есть IT-отдел, но нет системности: мониторинг «на глаз», бэкапы «примерно делаются», AD/DNS без аудита.",
    outcome: "Silver: Ansible + Puppet + Loki + AD/GPO. Ваш IT-отдел занимается задачами бизнеса, а не рутиной.",
    plan: "Silver",
  },
];

export default function ForWhom() {
  return (
    <section
      data-testid="forwhom-section"
      id="forwhom"
      style={{
        padding: "104px 0",
        background: "#fff",
        borderBottom: "1px solid var(--rule)",
      }}
    >
      <div className="wrap">
        <div
          className="reveal"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 60,
            alignItems: "end",
            marginBottom: 64,
            paddingBottom: 40,
            borderBottom: "1px solid var(--rule)",
          }}
        >
          <div>
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              Для кого
            </div>
            <h2 className="h-section">
              Три типа бизнеса,
              <br />
              где <em>IT критичен</em>
            </h2>
          </div>
          <p className="section-lead">
            Мы не берём всех подряд. Работаем только там, где IT-инфраструктура
            напрямую влияет на деньги — и где системный подход экономит
            больше, чем стоит. Если это про вас — поговорим.
          </p>
        </div>

        <div
          className="for-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 0,
            border: "1px solid var(--rule)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {SEGMENTS.map(({ Icon, tag, title, size, pain, outcome, plan }, i) => (
            <div
              key={tag}
              data-testid={`segment-${i}`}
              className={`reveal ${i > 0 ? `reveal-d${i}` : ""} for-cell`}
              style={{
                padding: 32,
                borderRight: i === 2 ? "none" : "1px solid var(--rule)",
                background: "#fff",
                transition: "background .2s",
              }}
            >
              <Icon size={26} color="var(--forest)" strokeWidth={1.4} />
              <div
                className="font-mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: ".14em",
                  textTransform: "uppercase",
                  color: "var(--stone-lt)",
                  marginTop: 18,
                  marginBottom: 6,
                }}
              >
                {tag} · {plan}
              </div>
              <h3
                className="font-display"
                style={{
                  fontSize: 22,
                  fontWeight: 500,
                  color: "var(--ink)",
                  letterSpacing: "-.01em",
                  marginBottom: 6,
                }}
              >
                {title}
              </h3>
              <div style={{ fontSize: 12.5, color: "var(--stone-lt)", marginBottom: 18 }}>
                {size}
              </div>

              <Block label="Типичная боль" text={pain} />
              <Block label="Наше решение" text={outcome} accent />
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .for-cell:hover { background: var(--cream) !important; }
        @media (max-width: 960px) {
          .for-grid { grid-template-columns: 1fr !important; }
          .for-cell { border-right: none !important; border-bottom: 1px solid var(--rule); }
          .for-cell:last-child { border-bottom: none; }
        }
      `}</style>
    </section>
  );
}

function Block({ label, text, accent }) {
  return (
    <div style={{ marginTop: 14 }}>
      <div
        className="font-mono"
        style={{
          fontSize: 10.5,
          letterSpacing: ".1em",
          textTransform: "uppercase",
          color: accent ? "var(--forest)" : "var(--stone-lt)",
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <p style={{ fontSize: 14, color: "var(--ink-2)", lineHeight: 1.6 }}>{text}</p>
    </div>
  );
}
