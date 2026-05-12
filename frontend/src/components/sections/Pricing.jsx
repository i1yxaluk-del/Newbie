import { Check } from "lucide-react";

const PLANS = [
  {
    id: "bronze",
    eyebrow: "Тариф 01",
    name: "Bronze",
    tagline: "1–5 серверов · малый бизнес",
    price: "25 000",
    setup: "Запуск 15–25 000 ₽",
    features: [
      { ok: true, text: "Мониторинг 24/7" },
      { ok: true, text: "Алерты в согласованных каналах" },
      { ok: true, text: "Ежедневные бэкапы + автопроверка" },
      { ok: true, text: "Реакция P1 — до 4 часов" },
      { ok: true, text: "Bastion VPN-доступ" },
      { ok: true, text: "Еженедельный отчёт" },
    ],
    limit: "1–2 ч ручной работы / мес",
    cta: "Начать с Bronze",
    featured: false,
  },
  {
    id: "silver",
    eyebrow: "Тариф 02 · рекомендуем",
    name: "Silver",
    tagline: "Windows + Linux · AD / DNS / GPO",
    price: "50 000",
    setup: "Запуск 30–50 000 ₽",
    features: [
      { ok: true, text: "Всё из Bronze", bold: true },
      { ok: true, text: "Автоматизация (Ansible + Puppet)" },
      { ok: true, text: "Поддержка AD · DNS · GPO" },
      { ok: true, text: "Централизованные логи (Loki)" },
      { ok: true, text: "Конфигурации в Git (IaC)" },
      { ok: true, text: "Реакция P1 — до 2 часов" },
    ],
    limit: "до 3 ч ручной работы / мес",
    cta: "Начать с Silver",
    featured: true,
  },
  {
    id: "gold",
    eyebrow: "Тариф 03",
    name: "Gold",
    tagline: "Wazuh SIEM + Kaspersky · 152-ФЗ",
    price: "85 000",
    setup: "Запуск 45–80 000 ₽",
    features: [
      { ok: true, text: "Всё из Silver", bold: true },
      { ok: true, text: "SIEM Wazuh + Kaspersky Security" },
      { ok: true, text: "Контроль уязвимостей (CVE-scan)" },
      { ok: true, text: "SLA-отчёты с метриками" },
      { ok: true, text: "Реакция P1 — до 1 часа · 24/7", bold: true },
      { ok: true, text: "Пост-мортем после P1" },
    ],
    limit: "до 4–5 ч ручной работы / мес",
    cta: "Начать с Gold",
    featured: false,
  },
];

export default function Pricing() {
  const onPick = (id) => {
    // Sync tariff to CTA form via custom event (survives React re-renders)
    window.dispatchEvent(new CustomEvent("msp:set-tariff", { detail: id }));
    const form = document.getElementById("audit");
    if (form) form.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <section
      data-testid="pricing-section"
      id="pricing"
      style={{
        padding: "120px 0",
        background: "#0e0c0a",
        color: "#f5f1e8",
        borderBottom: "1px solid rgba(255,255,255,.06)",
      }}
    >
      <div className="wrap">
        <div className="reveal section-header" style={{ color: "#f5f1e8" }}>
          <div>
            <div
              className="tag-dot"
              style={{ marginBottom: 18, color: "rgba(255,255,255,.55)" }}
            >
              Тарифы · цены 2026
            </div>
            <h2
              className="h-section"
              style={{ color: "#f5f1e8" }}
            >
              Три уровня
              <br />
              <em style={{ color: "#5fc9a2", fontStyle: "italic" }}>контроля</em>
            </h2>
          </div>
          <p
            className="section-lead"
            style={{ color: "rgba(241,237,228,.65)" }}
          >
            Фиксированная плата без скрытых начислений.
            Безнал · счёт · акт.
          </p>
        </div>

        <div
          className="pricing-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 2,
            background: "var(--rule)",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {PLANS.map((p, i) => (
            <div
              key={p.id}
              data-testid={`plan-${p.id}`}
              className={`reveal ${i > 0 ? `reveal-d${i}` : ""}`}
              style={{
                background: p.featured ? "var(--forest)" : "var(--cream)",
                color: p.featured ? "#fff" : "var(--ink)",
                padding: "38px 32px",
                position: "relative",
                transition: "background .2s",
              }}
            >
              <div
                className="font-mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: ".14em",
                  textTransform: "uppercase",
                  fontWeight: 500,
                  color: p.featured ? "rgba(255,255,255,.7)" : "var(--stone)",
                  marginBottom: 10,
                }}
              >
                {p.eyebrow}
              </div>
              <div
                className="font-display"
                style={{
                  fontSize: 30,
                  fontWeight: 500,
                  color: p.featured ? "#fff" : "var(--ink)",
                  marginBottom: 4,
                  letterSpacing: "-.01em",
                }}
              >
                {p.name}
              </div>
              <div
                style={{
                  fontSize: 14,
                  color: p.featured ? "rgba(255,255,255,.78)" : "var(--ink-2)",
                  opacity: p.featured ? 1 : 0.78,
                  marginBottom: 28,
                  lineHeight: 1.45,
                  whiteSpace: "pre-line",
                }}
              >
                {p.tagline}
              </div>

              <div
                style={{
                  padding: "20px 0",
                  marginBottom: 22,
                  borderTop: `1px solid ${p.featured ? "rgba(255,255,255,.15)" : "var(--rule)"}`,
                  borderBottom: `1px solid ${p.featured ? "rgba(255,255,255,.15)" : "var(--rule)"}`,
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--fm)",
                    letterSpacing: ".08em",
                    textTransform: "uppercase",
                    color: p.featured ? "rgba(255,255,255,.6)" : "var(--stone)",
                    display: "block",
                    marginBottom: 4,
                  }}
                >
                  от
                </span>
                <div
                  className="font-display"
                  style={{
                    fontSize: 42,
                    fontWeight: 500,
                    color: p.featured ? "#fff" : "var(--ink)",
                    letterSpacing: "-.02em",
                    lineHeight: 1,
                  }}
                >
                  {p.price}{" "}
                  <span style={{ fontSize: 22, fontWeight: 300 }}>₽</span>
                </div>
                <div
                  style={{
                    fontSize: 14,
                    color: p.featured ? "rgba(255,255,255,.7)" : "var(--stone)",
                    marginTop: 6,
                  }}
                >
                  в месяц
                </div>
                <div
                  className="font-mono"
                  style={{
                    fontSize: 11,
                    color: p.featured ? "rgba(255,255,255,.55)" : "var(--stone)",
                    marginTop: 8,
                  }}
                >
                  {p.setup}
                </div>
              </div>

              <ul style={{ listStyle: "none", padding: 0, marginBottom: 28 }}>
                {p.features.map((f, idx) => (
                  <li
                    key={idx}
                    style={{
                      display: "flex",
                      gap: 12,
                      alignItems: "flex-start",
                      fontSize: 14.5,
                      padding: "10px 0",
                      borderBottom: `1px solid ${p.featured ? "rgba(255,255,255,.10)" : "var(--rule-lt)"}`,
                      color: p.featured ? "rgba(255,255,255,.92)" : "var(--ink-2)",
                      lineHeight: 1.4,
                    }}
                  >
                    <Check
                      size={15}
                      strokeWidth={2.4}
                      color={p.featured ? "#5fc9a2" : "var(--forest)"}
                      style={{ flexShrink: 0, marginTop: 2 }}
                    />
                    <span style={{ fontWeight: f.bold ? 600 : 450 }}>{f.text}</span>
                  </li>
                ))}
              </ul>

              <div
                className="font-mono"
                style={{
                  fontSize: 11,
                  letterSpacing: ".04em",
                  color: p.featured ? "rgba(255,255,255,.7)" : "var(--stone)",
                  marginBottom: 20,
                  padding: "10px 14px",
                  background: p.featured ? "rgba(255,255,255,.10)" : "var(--cream-deep)",
                  borderRadius: 4,
                }}
              >
                ⟶ Лимит: {p.limit}
              </div>

              <button
                data-testid={`plan-${p.id}-cta`}
                onClick={() => onPick(p.id)}
                className={p.featured ? "btn-core btn-light" : "btn-core btn-secondary"}
                style={{ width: "100%", padding: 13 }}
              >
                {p.cta}
              </button>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) {
          .pricing-grid { grid-template-columns: 1fr !important; background: none !important; border: none !important; gap: 16px !important; }
          .pricing-grid > div { border: 1px solid var(--rule); border-radius: 8px; }
        }
      `}</style>
    </section>
  );
}
