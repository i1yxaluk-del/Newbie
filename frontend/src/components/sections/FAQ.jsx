import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";

const QA = [
  {
    q: "Чем это отличается от штатного системного администратора?",
    a: "Штатный сисадмин — зависимость от одного человека, 70–150k ₽/мес «в пусто». Наш сервис — автоматизированная система: мониторинг, бэкапы, алерты работают 24/7 вне зависимости от отпусков. Фиксированная плата, прозрачная отчётность, договор с SLA.",
  },
  {
    q: "А если сломается ночью в воскресенье?",
    a: "Автоматизированный мониторинг работает 24/7 и обнаруживает проблему раньше, чем она скажется на бизнесе. Реакция на P1 — вне рабочего окна в любой день. Gold — до 1 часа, Silver — до 2, Bronze — до 4. Все цифры в договоре.",
  },
  {
    q: "Сколько времени займёт подключение?",
    a: "1–3 рабочих дня от получения доступов до работающего мониторинга и первого бэкапа. Полная настройка автоматизации (Silver / Gold) — до 1 недели.",
  },
  {
    q: "Данные хранятся в России? Это соответствует 152-ФЗ?",
    a: "Да. Вся инфраструктура на дата-центрах в РФ. Бэкапы шифруются AES-256 на стороне клиента до отправки. Заключаем договор-поручение на обработку ПДн. Ключи шифрования остаются у вас.",
  },
  {
    q: "Что происходит при расторжении договора?",
    a: "Вы сохраняете инфраструктуру и данные. Передаём конфигурации из Git, ключи доступа, резервные копии и документацию. Уведомление за 30 дней. Никакой технологической зависимости — можете обслуживать сами или передать другому подрядчику.",
  },
  {
    q: "Как происходит оплата и документооборот?",
    a: "ИП на УСН (или НПД на старте). Счёт в начале месяца, предоплата, закрывающий акт после оказания услуг. ЭДО для юрлиц (СБИС / Диадок). Налоги платим сами — вы получаете полный пакет документов для бухгалтерии.",
  },
];

export default function FAQ() {
  return (
    <section
      data-testid="faq-section"
      id="faq"
      style={{ padding: "104px 0", borderBottom: "1px solid var(--rule)" }}
    >
      <div className="wrap wrap-sm">
        <div className="reveal" style={{ textAlign: "center", marginBottom: 48 }}>
          <div
            className="tag-dot"
            style={{ marginBottom: 18, justifyContent: "center" }}
          >
            Частые вопросы
          </div>
          <h2 className="h-section">
            Отвечаем <em>по делу</em>
          </h2>
        </div>

        <Accordion
          type="single"
          collapsible
          className="reveal"
          data-testid="faq-accordion"
          style={{
            background: "#fff",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {QA.map((item, i) => (
            <AccordionItem
              key={i}
              value={`q-${i}`}
              data-testid={`faq-item-${i}`}
              style={{
                borderBottom: i === QA.length - 1 ? "none" : "1px solid var(--rule-lt)",
              }}
            >
              <AccordionTrigger
                style={{
                  padding: "22px 28px",
                  fontFamily: "var(--fd)",
                  fontSize: 18,
                  fontWeight: 500,
                  color: "var(--ink)",
                  letterSpacing: "-.01em",
                  textAlign: "left",
                }}
              >
                {item.q}
              </AccordionTrigger>
              <AccordionContent
                style={{
                  padding: "0 28px 22px",
                  fontFamily: "var(--fb)",
                  fontSize: 14.5,
                  color: "var(--stone)",
                  lineHeight: 1.7,
                }}
              >
                {item.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
