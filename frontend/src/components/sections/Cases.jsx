const CASES = [
  {
    segment: "Юридическая компания",
    size: "45 сотрудников · 6 серверов · Москва",
    plan: "Silver",
    before: [
      "1С падала 1–2 раза в квартал — узнавали от юристов",
      "Бэкапы на внешний HDD в офисе, успешность не проверяли",
      "Изменения в AD вносил «приходящий» сисадмин, журнала нет",
    ],
    after: [
      "Среднее время обнаружения инцидента — < 3 минут",
      "Ежедневная проверка восстановления бэкапа (автотест)",
      "Все изменения — через Puppet + Git, история за 12 месяцев",
    ],
    metric: "0 незапланированных простоев за 6 месяцев",
  },
  {
    segment: "Частная медицинская клиника",
    size: "18 врачей · 32 ПК · Петербург",
    plan: "Gold",
    before: [
      "Просрочка обновлений ОС > 6 месяцев на половине ПК",
      "Отсутствие журнала доступа к МИС — риск по 152-ФЗ",
      "Антивирус установлен, но не централизован",
    ],
    after: [
      "Kaspersky Security Center — единая консоль и отчёты",
      "Wazuh SIEM: детекция подозрительного доступа в реальном времени",
      "Документированный регламент доступа + журналы для Роскомнадзора",
    ],
    metric: "Успешно прошли плановую проверку Росздравнадзора",
  },
  {
    segment: "Торгово-производственная компания",
    size: "120 сотрудников · 11 серверов · два филиала",
    plan: "Silver → Gold",
    before: [
      "Два IT-специалиста тушили пожары по 60% рабочего времени",
      "«Эталонные» настройки — в голове одного человека",
      "При уходе сотрудника домены/доступы уходили вместе с ним",
    ],
    after: [
      "Ansible playbook разворачивает новый филиал за 40 минут",
      "Все конфиги в Git: новый специалист включается за день",
      "Роли и доступы — через GPO-baseline, отзыв за 5 минут",
    ],
    metric: "IT-отдел переключился на развитие, а не поддержку",
  },
];

export default function Cases() {
  return (
    <section
      data-testid="cases-section"
      style={{
        padding: "104px 0",
        background: "var(--cream-deep)",
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
            marginBottom: 56,
            paddingBottom: 40,
            borderBottom: "1px solid var(--rule)",
          }}
        >
          <div>
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              Кейсы · 2025
            </div>
            <h2 className="h-section">
              Было <em>и стало</em>
            </h2>
          </div>
          <p className="section-lead">
            Ниже — обезличенные примеры из практики. Цифры усреднены, названия
            не раскрываются по соглашению о конфиденциальности. Подробные
            референсы предоставляются по запросу под NDA.
          </p>
        </div>

        <div
          className="cases-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 24,
          }}
        >
          {CASES.map((c, i) => (
            <article
              key={i}
              data-testid={`case-${i}`}
              className={`reveal ${i > 0 ? `reveal-d${i}` : ""}`}
              style={{
                background: "#fff",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                padding: 28,
              }}
            >
              <div
                className="font-mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: ".14em",
                  textTransform: "uppercase",
                  color: "var(--forest)",
                  marginBottom: 6,
                }}
              >
                {c.plan}
              </div>
              <h3
                className="font-display"
                style={{
                  fontSize: 22,
                  fontWeight: 500,
                  color: "var(--ink)",
                  marginBottom: 4,
                  letterSpacing: "-.01em",
                }}
              >
                {c.segment}
              </h3>
              <div style={{ fontSize: 12.5, color: "var(--stone-lt)", marginBottom: 22 }}>
                {c.size}
              </div>

              <CaseList title="Было" items={c.before} tone="mute" />
              <CaseList title="Стало" items={c.after} tone="accent" />

              <div
                style={{
                  marginTop: 18,
                  padding: "12px 14px",
                  background: "var(--forest-dim)",
                  border: "1px solid var(--forest-bdr)",
                  borderRadius: 4,
                  fontSize: 13,
                  color: "var(--forest)",
                  fontWeight: 500,
                }}
              >
                {c.metric}
              </div>
            </article>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) { .cases-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </section>
  );
}

function CaseList({ title, items, tone }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div
        className="font-mono"
        style={{
          fontSize: 10.5,
          letterSpacing: ".1em",
          textTransform: "uppercase",
          color: tone === "accent" ? "var(--forest)" : "var(--stone-lt)",
          marginBottom: 8,
        }}
      >
        {title}
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {items.map((it, i) => (
          <li
            key={i}
            style={{
              position: "relative",
              paddingLeft: 14,
              fontSize: 13.5,
              color: "var(--ink-2)",
              lineHeight: 1.55,
              marginBottom: 6,
            }}
          >
            <span
              style={{
                position: "absolute",
                left: 0,
                top: 8,
                width: 6,
                height: 1,
                background: tone === "accent" ? "var(--forest)" : "var(--stone-lt)",
              }}
              aria-hidden
            />
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}
