// Dark final CTA, before footer.
// Antimetal-style: massive heading, single primary action, minimal text.

export default function FinalCta() {
  return (
    <section
      data-testid="final-cta"
      style={{
        padding: "120px 0",
        background: "#0e0c0a",
        color: "#f5f1e8",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(60% 60% at 50% 100%, rgba(95,201,162,.10) 0%, transparent 65%)",
          pointerEvents: "none",
        }}
      />
      <div className="wrap" style={{ position: "relative", textAlign: "center" }}>
        <div
          className="tag-dot"
          style={{
            color: "rgba(255,255,255,.55)",
            justifyContent: "center",
            display: "flex",
            marginBottom: 24,
          }}
        >
          <span style={{ background: "#5fc9a2" }} />
          Готовы к старту
        </div>

        <h2
          className="font-display"
          style={{
            fontSize: "clamp(44px, 6vw, 80px)",
            lineHeight: 1.04,
            letterSpacing: "-.03em",
            color: "#f5f1e8",
            fontWeight: 500,
            marginBottom: 24,
            maxWidth: 920,
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          Бесплатный аудит
          <br />
          инфраструктуры за{" "}
          <em style={{ color: "#5fc9a2", fontStyle: "italic" }}>3 рабочих дня.</em>
        </h2>

        <p
          style={{
            fontSize: 17,
            color: "rgba(241,237,228,.65)",
            lineHeight: 1.6,
            maxWidth: 640,
            margin: "0 auto 40px",
            fontWeight: 300,
          }}
        >
          Отчёт со списком рисков · разбор бэкапов · рекомендация по тарифу.
          <br />
          Без обязательств.
        </p>

        <div
          style={{
            display: "flex",
            gap: 12,
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          <a
            href="#audit"
            className="btn-core"
            style={{
              background: "#f5f1e8",
              color: "#0e0c0a",
              fontWeight: 600,
              padding: "16px 32px",
              fontSize: 15.5,
            }}
          >
            Получить аудит →
          </a>
          <a
            href="#pricing"
            className="btn-core"
            style={{
              background: "transparent",
              color: "rgba(241,237,228,.85)",
              border: "1px solid rgba(241,237,228,.20)",
              padding: "16px 32px",
              fontSize: 15.5,
            }}
          >
            Сначала тарифы
          </a>
        </div>

        <div
          style={{
            marginTop: 56,
            paddingTop: 32,
            borderTop: "1px solid rgba(241,237,228,.10)",
            display: "flex",
            justifyContent: "center",
            gap: 48,
            flexWrap: "wrap",
            fontFamily: "var(--fm)",
            fontSize: 11,
            color: "rgba(241,237,228,.45)",
            letterSpacing: ".06em",
            textTransform: "uppercase",
          }}
        >
          <span>152-ФЗ ✓</span>
          <span>Реестр Минцифры ✓</span>
          <span>NDA по умолчанию</span>
          <span>Договор · оплата по счёту</span>
        </div>
      </div>
    </section>
  );
}
