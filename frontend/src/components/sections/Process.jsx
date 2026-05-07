const STEPS = [
  {
    d: "День 0",
    title: "Бесплатный экспресс-аудит",
    desc: "30 минут онлайн. Смотрим вашу инфраструктуру под view-доступом: бэкапы, открытые порты, диски, журналы входов. Показываем конкретные риски с цифрами.",
  },
  {
    d: "День 1–3",
    title: "КП, договор, развёртывание",
    desc: "В течение 24 часов присылаем персональное КП с обоснованием тарифа. Договор + SLA подписываем через ЭДО. Поднимаем Monitoring VM, Bastion + WireGuard, устанавливаем агенты на ваших серверах.",
  },
  {
    d: "Регулярно",
    title: "Сервис, отчёты, реакция по SLA",
    desc: "Еженедельный отчёт в Telegram или email. Реакция на инциденты по SLA из договора. Ежеквартальная встреча по стратегии IT.",
  },
];

export default function Process() {
  return (
    <section
      data-testid="process-section"
      id="process"
      style={{
        padding: "104px 0",
        background: "var(--cream)",
        borderBottom: "1px solid var(--rule)",
      }}
    >
      <div className="wrap">
        <div className="reveal section-header">
          <div>
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              Процесс подключения
            </div>
            <h2 className="h-section">
              От звонка <em>до продакшена</em>
              <br />
              за одну неделю
            </h2>
          </div>
          <p className="section-lead">
            Никаких многомесячных внедрений, согласований в 4 раунда и
            «поднимем за квартал». Стандартный онбординг — 2–3 рабочих дня.
            Полная автоматизация (Silver / Gold) — до 7 дней.
          </p>
        </div>

        <div className="process-steps">
          <div className="process-rule" aria-hidden />
          {STEPS.map((s, i) => (
            <div
              key={s.d}
              data-testid={`process-step-${i}`}
              className={`reveal process-step ${i > 0 ? `reveal-d${i % 3}` : ""}`}
              style={{
                borderBottom: i === STEPS.length - 1 ? "none" : "1px solid var(--rule-lt)",
              }}
            >
              <div className="process-step-date">
                <span
                  className="font-display"
                  style={{
                    fontSize: 22,
                    fontWeight: 500,
                    color: "var(--ink)",
                    letterSpacing: "-.01em",
                  }}
                >
                  {s.d}
                </span>
              </div>
              <div>
                <h3
                  className="font-display"
                  style={{
                    fontSize: 22,
                    fontWeight: 500,
                    color: "var(--ink)",
                    marginBottom: 6,
                    letterSpacing: "-.01em",
                  }}
                >
                  {s.title}
                </h3>
                <p
                  style={{
                    fontSize: 15,
                    color: "var(--stone)",
                    lineHeight: 1.7,
                    maxWidth: 760,
                  }}
                >
                  {s.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .process-steps { position: relative; }
        .process-rule {
          position: absolute;
          left: 78px;
          top: 6px;
          bottom: 6px;
          width: 1px;
          background: var(--rule);
        }
        .process-step {
          display: grid;
          grid-template-columns: 160px minmax(0, 1fr);
          gap: 32px;
          padding: 28px 0;
          align-items: start;
        }
        .process-step > * { min-width: 0; }
        .process-step-date {
          display: flex;
          align-items: center;
          gap: 14px;
        }
        @media (max-width: 720px) {
          .process-rule { display: none; }
          .process-step {
            grid-template-columns: 1fr;
            gap: 12px;
            padding: 24px 0;
          }
          .process-step-date span { font-size: 18px !important; }
        }
      `}</style>
    </section>
  );
}
