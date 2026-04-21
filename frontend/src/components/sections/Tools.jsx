import {
  BarChart3,
  HardDrive,
  Shield,
  Settings,
  Radar,
  Cloud,
} from "lucide-react";

const TOOLS = [
  {
    Icon: BarChart3,
    name: "Prometheus + Grafana",
    desc: "Промышленный стек мониторинга. Метрики каждые 15 секунд, наглядные дашборды, умные алерты. Конфигурации — в Git, без «настроек на коленке».",
  },
  {
    Icon: HardDrive,
    name: "restic + Yandex S3",
    desc: "Шифрованные инкрементальные бэкапы с дедупликацией. Данные в России. Утренняя автопроверка каждого архива — не «примерно делается».",
  },
  {
    Icon: Shield,
    name: "WireGuard + Bastion",
    desc: "Современный VPN-протокол с минимальной атакуемой поверхностью. Все подключения через Bastion с полным журналированием действий.",
  },
  {
    Icon: Settings,
    name: "Ansible + Puppet",
    desc: "Ansible — «сделать и выйти». Puppet — постоянный контроль: если кто-то изменил настройки вручную, система вернёт к эталону через 30 минут.",
  },
  {
    Icon: Radar,
    name: "Wazuh SIEM · Gold",
    desc: "Детектирование угроз, контроль целостности файлов, CVE-сканирование. Не «один антивирус», а полноценный слой обнаружения инцидентов безопасности.",
  },
  {
    Icon: Cloud,
    name: "Yandex Cloud",
    desc: "Вся инфраструктура в России. Официальный Terraform-провайдер, S3-совместимое хранилище, соответствие 152-ФЗ, гранты для старта.",
  },
];

export default function Tools() {
  return (
    <section
      data-testid="tools-section"
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
            marginBottom: 56,
            paddingBottom: 40,
            borderBottom: "1px solid var(--rule)",
          }}
        >
          <div>
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              Технологии
            </div>
            <h2 className="h-section">
              Только проверенный
              <br />
              <em>инструментарий</em>
            </h2>
          </div>
          <p className="section-lead">
            Каждый инструмент выбран за надёжность и соответствие требованиям
            российского рынка — данные в РФ, открытый код там, где это важно,
            коммерческие решения там, где нужны гарантии.
          </p>
        </div>

        <div
          className="tools-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 0,
            border: "1px solid var(--rule)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {TOOLS.map(({ Icon, name, desc }, i) => (
            <div
              key={name}
              data-testid={`tool-${i}`}
              className={`reveal ${i > 0 ? `reveal-d${i % 3}` : ""} tool-cell`}
              style={{
                padding: "32px 28px",
                borderRight: (i + 1) % 3 === 0 ? "none" : "1px solid var(--rule)",
                borderBottom: i < 3 ? "1px solid var(--rule)" : "none",
                transition: "background .2s",
              }}
            >
              <Icon size={22} color="var(--forest)" strokeWidth={1.5} />
              <div
                className="font-display"
                style={{
                  fontSize: 19,
                  fontWeight: 500,
                  marginTop: 16,
                  marginBottom: 8,
                  color: "var(--ink)",
                  letterSpacing: "-.01em",
                }}
              >
                {name}
              </div>
              <p style={{ fontSize: 13.5, color: "var(--stone)", lineHeight: 1.65 }}>
                {desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .tool-cell:hover { background: var(--cream); }
        @media (max-width: 960px) { .tools-grid { grid-template-columns: 1fr 1fr !important; } }
        @media (max-width: 620px) { .tools-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </section>
  );
}
