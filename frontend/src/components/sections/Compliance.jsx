import { MapPin, FileCheck, Package, KeyRound, FileSignature, ScrollText } from "lucide-react";

const ITEMS = [
  {
    Icon: MapPin,
    title: "Данные — в России",
    text: "Вся инфраструктура мониторинга развёрнута в Yandex Cloud (дата-центры Москва, Санкт-Петербург). Хранение и обработка ПДн соответствуют 152-ФЗ.",
  },
  {
    Icon: FileCheck,
    title: "152-ФЗ по умолчанию",
    text: "Договор-поручение на обработку ПДн, модель угроз, регламент доступа, журнал действий. Готовые документы для предъявления Роскомнадзору при проверке.",
  },
  {
    Icon: Package,
    title: "Импортозамещение — дружелюбно",
    text: "Поддержка Astra Linux, ALT Linux, РЕД ОС, Postgres Pro. Мониторинг работает одинаково на Windows, Linux-дистрибутивах и отечественных ОС — без привязки к вендору.",
  },
  {
    Icon: KeyRound,
    title: "Шифрование на всех уровнях",
    text: "AES-256 для бэкапов до отправки в облако. WireGuard-туннели между площадками. TLS для всех HTTP-эндпоинтов. Ключи — у вас, не у нас.",
  },
  {
    Icon: FileSignature,
    title: "Договор с прописанным SLA",
    text: "ИП на УСН, официальные счета и акты, ЭДО для юрлиц. SLA-метрики вынесены в приложение к договору: что именно мы гарантируем и что происходит при нарушении.",
  },
  {
    Icon: ScrollText,
    title: "Прозрачный выход из сервиса",
    text: "При расторжении вы получаете все конфигурации из Git, ключи, резервные копии и документацию. Никакой зависимости от нас — уведомление за 30 дней.",
  },
];

export default function Compliance() {
  return (
    <section
      data-testid="compliance-section"
      id="compliance"
      style={{
        padding: "104px 0",
        background: "var(--cream-deep)",
        borderBottom: "1px solid var(--rule)",
        borderTop: "1px solid var(--rule)",
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
              Соответствие требованиям РФ · 2026
            </div>
            <h2 className="h-section">
              Законно, <em>суверенно</em>,
              <br />
              предсказуемо
            </h2>
          </div>
          <p className="section-lead">
            Работаем в российском правовом поле. Используем стек, совместимый
            с требованиями регуляторов и импортозамещением. Документы готовы к
            любой проверке — от налоговой до Роскомнадзора.
          </p>
        </div>

        <div
          className="comp-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 1,
            background: "var(--rule)",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {ITEMS.map(({ Icon, title, text }, i) => (
            <div
              key={title}
              data-testid={`compliance-item-${i}`}
              className={`reveal ${i > 0 ? `reveal-d${i % 3}` : ""}`}
              style={{
                padding: 32,
                background: "#fff",
                transition: "background .2s",
              }}
            >
              <Icon size={22} color="var(--forest)" strokeWidth={1.5} />
              <h3
                className="font-display"
                style={{
                  fontSize: 20,
                  fontWeight: 500,
                  marginTop: 18,
                  marginBottom: 10,
                  color: "var(--ink)",
                  letterSpacing: "-.01em",
                }}
              >
                {title}
              </h3>
              <p style={{ fontSize: 14, color: "var(--stone)", lineHeight: 1.65 }}>{text}</p>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) { .comp-grid { grid-template-columns: 1fr 1fr !important; } }
        @media (max-width: 620px) { .comp-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </section>
  );
}
