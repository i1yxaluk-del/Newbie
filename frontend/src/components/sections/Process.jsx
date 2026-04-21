const STEPS = [
  {
    d: "День 0",
    title: "Бесплатный экспресс-аудит",
    desc: "30 минут онлайн. Смотрим вашу инфраструктуру под view-доступом: бэкапы, открытые порты, диски, журналы входов. Показываем конкретные риски с цифрами.",
  },
  {
    d: "День 1",
    title: "КП и договор",
    desc: "В течение 24 часов присылаем персональное КП с обоснованием тарифа. Договор типовой (Bronze / Silver / Gold) + приложение SLA. Подписание через ЭДО или скан.",
  },
  {
    d: "День 2–3",
    title: "Развёртывание",
    desc: "Поднимаем Monitoring VM в Yandex Cloud, настраиваем Bastion + WireGuard, устанавливаем агенты на ваших серверах, запускаем первые бэкапы.",
  },
  {
    d: "Неделя 1",
    title: "Калибровка и обучение",
    desc: "Настраиваем пороги алертов под ваш трафик, передаём доступы, обучаем ответственного от клиента пользоваться дашбордами Grafana и отчётами.",
  },
  {
    d: "Регулярно",
    title: "Сервис и отчёты",
    desc: "Еженедельный отчёт в Telegram/email. Ежемесячный — с трендами. Реакция на инциденты по SLA. Ежеквартальная встреча по стратегии IT.",
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

        <div style={{ position: "relative" }}>
          <div
            style={{
              position: "absolute",
              left: 78,
              top: 6,
              bottom: 6,
              width: 1,
              background: "var(--rule)",
            }}
            aria-hidden
          />
          {STEPS.map((s, i) => (
            <div
              key={s.d}
              data-testid={`process-step-${i}`}
              className={`reveal ${i > 0 ? `reveal-d${i % 3}` : ""}`}
              style={{
                display: "grid",
                gridTemplateColumns: "160px 1fr",
                gap: 32,
                padding: "28px 0",
                borderBottom: i === STEPS.length - 1 ? "none" : "1px solid var(--rule-lt)",
                alignItems: "start",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
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
    </section>
  );
}
