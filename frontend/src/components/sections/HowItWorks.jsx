import { Activity, HardDrive, Lock, FileText } from "lucide-react";

const STEPS = [
  {
    num: "01",
    title: "Мониторинг",
    desc: "Prometheus опрашивает серверы каждые 15 секунд. Grafana визуализирует. Alertmanager отправляет уведомления в Telegram до того, как проблема повлияет на бизнес.",
    tools: ["Prometheus", "Grafana", "Alertmanager"],
    Icon: Activity,
  },
  {
    num: "02",
    title: "Бэкапы",
    desc: "Ежедневное шифрованное копирование в Yandex Object Storage. Автоматическая проверка каждое утро. Тестовое восстановление по расписанию — а не «когда-нибудь потом».",
    tools: ["restic", "Yandex S3", "AES-256"],
    Icon: HardDrive,
  },
  {
    num: "03",
    title: "Защищённый доступ",
    desc: "WireGuard VPN + Bastion-сервер. Никаких открытых RDP/SSH в интернет. Все подключения через зашифрованный туннель с журналом действий.",
    tools: ["WireGuard", "Bastion", "nftables"],
    Icon: Lock,
  },
  {
    num: "04",
    title: "Отчёты и SLA",
    desc: "Еженедельный отчёт о состоянии инфраструктуры. Реакция на критические инциденты — по чётко прописанному SLA в договоре, а не «когда удобно».",
    tools: ["Weekly report", "SLA", "Git IaC"],
    Icon: FileText,
  },
];

export default function HowItWorks() {
  return (
    <section
      data-testid="how-section"
      id="how"
      style={{ padding: "104px 0", borderBottom: "1px solid var(--rule)" }}
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
              Принцип работы
            </div>
            <h2 className="h-section">
              Автоматизация
              <br />
              вместо ручного труда
            </h2>
          </div>
          <p className="section-lead">
            Мы не продаём «безлимитного администратора». Мы строим
            автоматизированную систему, которая работает сама. Человек
            подключается только там, где действительно нужна экспертиза.
          </p>
        </div>

        <div
          className="how-grid"
          style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0 }}
        >
          {STEPS.map(({ num, title, desc, tools, Icon }, i) => (
            <div
              key={num}
              className={`reveal ${i > 0 ? `reveal-d${i}` : ""}`}
              style={{
                padding: "28px 24px",
                borderRight: i === 3 ? "none" : "1px solid var(--rule)",
                paddingLeft: i === 0 ? 0 : 24,
                paddingRight: i === 3 ? 0 : 24,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  marginBottom: 14,
                }}
              >
                <span
                  className="font-display"
                  style={{
                    fontSize: 48,
                    fontWeight: 300,
                    color: "var(--cream-deep)",
                    lineHeight: 1,
                    letterSpacing: "-.03em",
                  }}
                >
                  {num}
                </span>
                <Icon size={20} color="var(--forest)" strokeWidth={1.6} />
              </div>
              <div
                className="font-display"
                style={{
                  fontSize: 20,
                  fontWeight: 500,
                  color: "var(--ink)",
                  marginBottom: 10,
                  letterSpacing: "-.01em",
                }}
              >
                {title}
              </div>
              <p style={{ fontSize: 14, color: "var(--stone)", lineHeight: 1.65 }}>{desc}</p>
              <div
                style={{
                  marginTop: 16,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 6,
                }}
              >
                {tools.map((t) => (
                  <span
                    key={t}
                    className="font-mono"
                    style={{
                      fontSize: 10,
                      letterSpacing: ".07em",
                      color: "var(--forest)",
                      background: "var(--forest-dim)",
                      border: "1px solid var(--forest-bdr)",
                      padding: "3px 8px",
                      borderRadius: 3,
                    }}
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) {
          .how-grid { grid-template-columns: 1fr 1fr !important; }
          .how-grid > div { border-right: none !important; padding: 24px 0 !important; border-bottom: 1px solid var(--rule); }
        }
      `}</style>
    </section>
  );
}
