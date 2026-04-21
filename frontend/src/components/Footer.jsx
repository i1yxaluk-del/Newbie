import { ShieldCheck } from "lucide-react";

export default function Footer() {
  return (
    <footer
      data-testid="main-footer"
      style={{
        borderTop: "1px solid var(--rule)",
        padding: "40px 0",
        background: "var(--cream)",
      }}
    >
      <div className="wrap">
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 24,
            flexWrap: "wrap",
          }}
        >
          <div style={{ maxWidth: 340 }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                fontFamily: "var(--fd)",
                fontSize: 18,
                fontWeight: 500,
                color: "var(--ink)",
              }}
            >
              <ShieldCheck size={16} color="var(--forest)" />
              MSP<em style={{ color: "var(--forest)", fontStyle: "normal" }}>Shield</em>
            </div>
            <p
              style={{
                fontSize: 12.5,
                color: "var(--stone-lt)",
                lineHeight: 1.6,
                marginTop: 10,
              }}
            >
              © 2026 MSPShield · Управляемый IT-сервис для бизнеса
              <br />
              <span style={{ opacity: 0.6 }}>
                ИП [Фамилия И.О.] · ИНН —— · ОГРНИП ——
              </span>
            </p>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              fontSize: 13,
            }}
          >
            <span
              className="font-mono"
              style={{
                fontSize: 10.5,
                letterSpacing: ".12em",
                textTransform: "uppercase",
                color: "var(--stone-lt)",
                marginBottom: 4,
              }}
            >
              Документы
            </span>
            <a
              href="/docs/privacy.html"
              data-testid="footer-privacy"
              style={{ color: "var(--stone)", textDecoration: "none" }}
            >
              Политика конфиденциальности
            </a>
            <a
              href="/docs/offer.html"
              data-testid="footer-offer"
              style={{ color: "var(--stone)", textDecoration: "none" }}
            >
              Публичная оферта
            </a>
            <a
              href="/docs/sla.html"
              data-testid="footer-sla"
              style={{ color: "var(--stone)", textDecoration: "none" }}
            >
              SLA
            </a>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              fontSize: 13,
            }}
          >
            <span
              className="font-mono"
              style={{
                fontSize: 10.5,
                letterSpacing: ".12em",
                textTransform: "uppercase",
                color: "var(--stone-lt)",
                marginBottom: 4,
              }}
            >
              Контакты
            </span>
            <a
              href="mailto:hello@mspshield.ru"
              data-testid="footer-email"
              style={{ color: "var(--stone)", textDecoration: "none" }}
            >
              hello@mspshield.ru
            </a>
            <a
              href="https://t.me/mspshield"
              data-testid="footer-tg"
              style={{ color: "var(--forest)", textDecoration: "none", fontFamily: "var(--fm)" }}
            >
              @mspshield
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
