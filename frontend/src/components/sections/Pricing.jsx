import { Check, Minus } from "lucide-react";

const PLANS = [
  {
    id: "bronze",
    eyebrow: "Тариф 01",
    name: "Bronze",
    tagline: "Базовая устойчивость\n1–5 серверов · малый бизнес",
    price: "25 000",
    setup: "Запуск: 15 000 – 25 000 ₽ разово",
    features: [
      { ok: true, text: "Мониторинг серверов 24/7" },
      { ok: true, text: "Алерты в Telegram при сбоях" },
      { ok: true, text: "Ежедневные бэкапы + автопроверка" },
      { ok: true, text: "Еженедельный отчёт" },
      { ok: true, text: "Консультация 1 ч/мес" },
      { ok: true, text: "Реакция P1 — до 4 часов" },
      { ok: true, text: "Bastion VPN-доступ" },
      { ok: false, text: "Автоматизация Ansible / Puppet" },
      { ok: false, text: "Поддержка AD / DNS / GPO" },
    ],
    limit: "⟶ Лимит: 1–2 ч ручной работы / мес",
    cta: "Начать с Bronze",
    featured: false,
  },
  {
    id: "silver",
    eyebrow: "Тариф 02 · Рекомендуем",
    name: "Silver",
    tagline: "Автоматизированное сопровождение\nWindows + Linux · AD / DNS / GPO",
    price: "50 000",
    setup: "Запуск: 30 000 – 50 000 ₽ разово",
    features: [
      { ok: true, text: "Всё из Bronze", bold: true },
      { ok: true, text: "Автоматизация (Ansible + Puppet)" },
      { ok: true, text: "Поддержка AD, DNS, GPO" },
      { ok: true, text: "Централизованные логи (Loki)" },
      { ok: true, text: "Ежемесячный отчёт с трендами" },
      { ok: true, text: "2–3 ч работ / консультаций" },
      { ok: true, text: "Конфигурации в Git (IaC)" },
      { ok: true, text: "Реакция P1 — до 2 часов" },
      { ok: false, text: "SIEM / Security мониторинг" },
    ],
    limit: "⟶ Лимит: до 3 ч ручной работы / мес",
    cta: "Начать с Silver",
    featured: true,
  },
  {
    id: "gold",
    eyebrow: "Тариф 03",
    name: "Gold",
    tagline: "Безопасность · SLA · Compliance\nWazuh SIEM + Kaspersky",
    price: "85 000",
    setup: "Запуск: 45 000 – 80 000 ₽ разово",
    features: [
      { ok: true, text: "Всё из Silver", bold: true },
      { ok: true, text: "SIEM Wazuh — детектирование угроз" },
      { ok: true, text: "Контроль уязвимостей (CVE-scan)" },
      { ok: true, text: "SLA-отчёты с метриками" },
      { ok: true, text: "Реакция P1 — до 1 часа · 24/7", bold: true },
      { ok: true, text: "Kaspersky Security Center" },
      { ok: true, text: "Тикет-система (osTicket)" },
      { ok: true, text: "Стратегическая IT-сессия / мес" },
      { ok: true, text: "Пост-мортем после P1" },
    ],
    limit: "⟶ Лимит: до 4–5 ч ручной работы / мес",
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
            marginBottom: 56,
            paddingBottom: 40,
            borderBottom: "1px solid var(--rule)",
          }}
        >
          <div>
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              Тарифы · цены 2026
            </div>
            <h2 className="h-section">
              Три уровня
              <br />
              <em>контроля</em>
            </h2>
          </div>
          <p className="section-lead">
            Прозрачная фиксированная плата, без скрытых начислений. Все
            тарифы включают мониторинг 24/7, автоматические бэкапы и
            еженедельный отчёт. Оплата — безнал, счёт + акт.
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
                  fontSize: 10,
                  letterSpacing: ".14em",
                  textTransform: "uppercase",
                  color: p.featured ? "rgba(255,255,255,.5)" : "var(--stone-lt)",
                  marginBottom: 8,
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
                  fontSize: 13,
                  color: p.featured ? "rgba(255,255,255,.6)" : "var(--stone-lt)",
                  marginBottom: 26,
                  lineHeight: 1.5,
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
                    fontSize: 12,
                    color: p.featured ? "rgba(255,255,255,.4)" : "var(--stone-lt)",
                    display: "block",
                    marginBottom: 2,
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
                    color: p.featured ? "rgba(255,255,255,.55)" : "var(--stone)",
                    marginTop: 4,
                  }}
                >
                  в месяц
                </div>
                <div
                  className="font-mono"
                  style={{
                    fontSize: 11,
                    color: p.featured ? "rgba(255,255,255,.4)" : "var(--stone-lt)",
                    marginTop: 6,
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
                      gap: 10,
                      alignItems: "flex-start",
                      fontSize: 13.5,
                      padding: "7px 0",
                      borderBottom: `1px solid ${p.featured ? "rgba(255,255,255,.08)" : "var(--rule-lt)"}`,
                      color: p.featured ? "rgba(255,255,255,.75)" : "var(--stone)",
                      opacity: f.ok ? 1 : 0.55,
                    }}
                  >
                    {f.ok ? (
                      <Check
                        size={14}
                        color={p.featured ? "#fff" : "var(--forest)"}
                        style={{ flexShrink: 0, marginTop: 3 }}
                      />
                    ) : (
                      <Minus
                        size={14}
                        color="var(--stone-lt)"
                        style={{ flexShrink: 0, marginTop: 3 }}
                      />
                    )}
                    <span style={{ fontWeight: f.bold ? 600 : 400 }}>{f.text}</span>
                  </li>
                ))}
              </ul>

              <div
                className="font-mono"
                style={{
                  fontSize: 11,
                  color: p.featured ? "rgba(255,255,255,.55)" : "var(--stone-lt)",
                  marginBottom: 18,
                  padding: "8px 12px",
                  background: p.featured ? "rgba(255,255,255,.08)" : "var(--cream-deep)",
                  borderRadius: 3,
                }}
              >
                {p.limit}
              </div>

              <button
                data-testid={`plan-${p.id}-cta`}
                onClick={() => onPick(p.id)}
                className={p.featured ? "btn-core btn-light" : "btn-core btn-ghost"}
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
