import { Check, Minus } from "lucide-react";

const ROWS = [
  ["Стоимость", "70–150k ₽/мес + налоги", "По факту работ, непредсказуемо", "Фиксированная абонентская плата"],
  ["Мониторинг 24/7", "Если сам настроит", "Нет — узнаёте от сотрудников", "Автоматически каждые 15 сек"],
  ["Реакция на сбой", "Когда придёт на работу", "Когда дозвонитесь", "По SLA (договор) — 1–4 часа"],
  ["Бэкапы с автопроверкой", "«Примерно делаются»", "Нет", "Ежедневно + утренняя проверка"],
  ["Отчётность", "Устно, если спросить", "Никакой", "Weekly + Monthly отчёты"],
  ["Отпуск / болезнь", "Инфраструктура без присмотра", "Не ваша проблема", "Автоматизация работает независимо"],
  ["Документация", "В голове одного человека", "Никакой", "Всё в Git, регламенты, DoD"],
  ["Юридическая защита", "Трудовой договор", "Часто физлицо, без ИП", "ИП + договор услуг + SLA"],
];

export default function Compare() {
  return (
    <section
      data-testid="compare-section"
      style={{
        padding: "104px 0",
        background: "#fff",
        borderBottom: "1px solid var(--rule)",
      }}
    >
      <div className="wrap">
        <div className="reveal">
          <div className="tag-dot" style={{ marginBottom: 18 }}>
            Сравнение
          </div>
          <h2 className="h-section">
            MSPShield <em>против</em>
            <br />
            других вариантов
          </h2>
        </div>

        <div style={{ overflowX: "auto", marginTop: 48 }}>
          <table
            data-testid="compare-table"
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 14.5,
              minWidth: 780,
            }}
          >
            <thead>
              <tr>
                <th style={thStyle}>Параметр</th>
                <th style={thStyle}>Штатный сисадмин</th>
                <th style={thStyle}>Фрилансер / по вызову</th>
                <th style={{ ...thStyle, ...ourTh }}>MSPShield</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([param, staff, freelance, ours]) => (
                <tr key={param}>
                  <td style={tdBold}>{param}</td>
                  <td style={tdStyle}>{staff}</td>
                  <td style={tdStyle}>{freelance}</td>
                  <td style={ourTd}>
                    <Check
                      size={15}
                      color="var(--forest)"
                      style={{ display: "inline-block", verticalAlign: "-3px", marginRight: 6 }}
                    />
                    {ours}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p
          style={{
            marginTop: 24,
            fontSize: 12.5,
            color: "var(--stone-lt)",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Minus size={12} /> Данные на основе средних показателей рынка РФ
          для компаний 15–150 сотрудников (2025–2026)
        </p>
      </div>
    </section>
  );
}

const thStyle = {
  padding: "14px 20px",
  textAlign: "left",
  fontWeight: 500,
  fontSize: 13,
  letterSpacing: ".02em",
  borderBottom: "2px solid var(--rule)",
  color: "var(--stone)",
  whiteSpace: "nowrap",
};
const ourTh = {
  background: "var(--forest)",
  color: "#fff",
  borderBottomColor: "var(--forest)",
  borderRadius: "4px 4px 0 0",
};
const tdStyle = {
  padding: "14px 20px",
  borderBottom: "1px solid var(--rule-lt)",
  color: "var(--stone)",
  verticalAlign: "middle",
};
const tdBold = { ...tdStyle, color: "var(--ink)", fontWeight: 500, whiteSpace: "nowrap" };
const ourTd = {
  ...tdStyle,
  background: "rgba(27,77,62,.04)",
  borderLeft: "1px solid var(--forest-bdr)",
  borderRight: "1px solid var(--forest-bdr)",
  color: "var(--ink)",
  fontWeight: 500,
};
