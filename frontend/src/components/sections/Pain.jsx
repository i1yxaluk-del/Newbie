import { useState, useMemo } from "react";
import { ArrowUpRight } from "lucide-react";

const PAIN_POINTS = [
  "О падении сервера узнаёте от сотрудников, не от системы",
  "Бэкапы делаются «примерно», рестор никто не проверял",
  "Непредсказуемые счета «по вызову», без гарантий",
];

const fmt = (n) => Math.round(n).toLocaleString("ru-RU") + " ₽";

// Accept digits only; forbid leading zeros so users never see a "hanging 0" in the field.
const sanitizeDigits = (raw) => {
  const onlyDigits = (raw || "").replace(/\D/g, "");
  return onlyDigits.replace(/^0+(?=\d)/, "");
};

export default function Pain() {
  // Stored as strings so the input can be empty while editing — no forced "0".
  const [revenue, setRevenue] = useState("3000000");
  const [days, setDays] = useState("22");
  const [hours, setHours] = useState("9");
  const [downtime, setDowntime] = useState(8);
  const [incidents, setIncidents] = useState(4);

  const calc = useMemo(() => {
    const revenueN = Number(revenue) || 0;
    const daysN = Number(days) || 22;
    const hoursN = Number(hours) || 9;
    const workHours = Math.max(1, daysN * hoursN);
    const hourCost = revenueN / workHours;
    const perIncident = hourCost * downtime;
    const yearLoss = perIncident * incidents;
    const serviceYear = 240_000; // Bronze annual
    const ratio = yearLoss / serviceYear;
    let verdict;
    if (ratio >= 5) {
      verdict = `Потери ${fmt(yearLoss)}/год — это в ${ratio.toFixed(1)}× больше годовой стоимости Bronze. Сервис окупается при первом предотвращённом инциденте.`;
    } else if (ratio >= 1.5) {
      verdict = `Потери от простоев (${fmt(yearLoss)}/год) в ${ratio.toFixed(1)}× превышают стоимость обслуживания — вложение обосновано.`;
    } else {
      verdict = `Даже при консервативных оценках окупаемость достигается при первом же предотвращённом инциденте.`;
    }
    return { hourCost, perIncident, yearLoss, serviceYear, verdict };
  }, [revenue, days, hours, downtime, incidents]);

  const handleBlur = (setter, fallback) => (e) => {
    if (!e.target.value) setter(String(fallback));
  };

  return (
    <section
      data-testid="pain-section"
      id="calc"
      style={{ padding: "104px 0", background: "var(--ink)", color: "#fff" }}
    >
      <div className="wrap">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 80,
            alignItems: "center",
          }}
          className="pain-grid-md"
        >
          <div className="reveal">
            <div
              className="tag-dot"
              style={{ color: "rgba(255,255,255,.5)", marginBottom: 20 }}
            >
              Почему это важно
            </div>
            <h2
              className="font-display"
              style={{
                fontSize: "clamp(36px, 4vw, 54px)",
                fontWeight: 400,
                lineHeight: 1.08,
                letterSpacing: "-.02em",
                color: "#fff",
                marginBottom: 20,
              }}
            >
              «Всё работает» —
              <br />
              <em style={{ fontStyle: "italic", color: "rgba(255,255,255,.45)" }}>
                пока не перестаёт
              </em>
            </h2>
            <p
              style={{
                fontSize: 17,
                color: "rgba(255,255,255,.65)",
                lineHeight: 1.6,
                marginBottom: 36,
                fontWeight: 400,
                maxWidth: 460,
              }}
            >
              Посчитайте, сколько стоит час простоя.
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {PAIN_POINTS.map((p) => (
                <li
                  key={p}
                  style={{
                    display: "flex",
                    gap: 14,
                    padding: "14px 0",
                    borderTop: "1px solid rgba(255,255,255,.07)",
                    fontSize: 15,
                    color: "rgba(255,255,255,.78)",
                  }}
                >
                  <ArrowUpRight
                    size={16}
                    color="rgba(255,255,255,.35)"
                    style={{ flexShrink: 0, marginTop: 3 }}
                  />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Calculator */}
          <div
            data-testid="roi-calculator"
            className="reveal reveal-d1"
            style={{
              background: "rgba(255,255,255,.04)",
              border: "1px solid rgba(255,255,255,.1)",
              borderRadius: 8,
              padding: 36,
            }}
          >
            <div
              className="font-display"
              style={{ fontSize: 24, color: "#fff", marginBottom: 6 }}
            >
              Калькулятор стоимости простоя
            </div>
            <div style={{ fontSize: 13, color: "rgba(255,255,255,.45)", marginBottom: 26 }}>
              Введите параметры — расчёт обновится автоматически
            </div>

            <CalcField label="Ежемесячная выручка (₽)">
              <input
                data-testid="calc-revenue"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={revenue}
                onFocus={(e) => e.target.select()}
                onChange={(e) => setRevenue(sanitizeDigits(e.target.value))}
                onBlur={handleBlur(setRevenue, 3000000)}
                className="calc-input"
              />
            </CalcField>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <CalcField label="Рабочих дней в месяце">
                <input
                  data-testid="calc-days"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={days}
                  onFocus={(e) => e.target.select()}
                  onChange={(e) => setDays(sanitizeDigits(e.target.value))}
                  onBlur={handleBlur(setDays, 22)}
                  className="calc-input"
                />
              </CalcField>
              <CalcField label="Часов в рабочем дне">
                <input
                  data-testid="calc-hours"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={hours}
                  onFocus={(e) => e.target.select()}
                  onChange={(e) => setHours(sanitizeDigits(e.target.value))}
                  onBlur={handleBlur(setHours, 9)}
                  className="calc-input"
                />
              </CalcField>
            </div>

            <CalcField label="Среднее время простоя при инциденте">
              <select
                data-testid="calc-downtime"
                value={downtime}
                onChange={(e) => setDowntime(Number(e.target.value))}
                className="calc-input"
              >
                <option value={2}>2 часа — быстрое обнаружение</option>
                <option value={4}>4 часа — среднее</option>
                <option value={8}>8 часов — обнаружили утром</option>
                <option value={24}>24 часа — критический сбой</option>
              </select>
            </CalcField>

            <CalcField label="Инцидентов в год без мониторинга">
              <select
                data-testid="calc-incidents"
                value={incidents}
                onChange={(e) => setIncidents(Number(e.target.value))}
                className="calc-input"
              >
                <option value={2}>2 — оптимистично</option>
                <option value={4}>4 — реалистично</option>
                <option value={6}>6 — типично</option>
                <option value={12}>12 — часто</option>
              </select>
            </CalcField>

            <div
              data-testid="calc-result"
              style={{
                marginTop: 22,
                padding: 20,
                background: "rgba(27,77,62,.18)",
                border: "1px solid rgba(27,77,62,.4)",
                borderRadius: 6,
              }}
            >
              <CalcRow label="Стоимость 1 часа простоя" value={fmt(calc.hourCost)} />
              <CalcRow
                label="Потери за один инцидент"
                value={fmt(calc.perIncident)}
                tone="danger"
              />
              <CalcRow
                label="Потери за год (без мониторинга)"
                value={fmt(calc.yearLoss)}
                tone="danger"
              />
              <CalcRow
                label="Стоимость Bronze-тарифа в год"
                value={fmt(calc.serviceYear)}
                tone="safe"
                bold
              />
            </div>

            <p
              data-testid="calc-verdict"
              style={{
                marginTop: 16,
                fontSize: 13.5,
                color: "rgba(255,255,255,.55)",
                lineHeight: 1.6,
                fontStyle: "italic",
              }}
            >
              {calc.verdict}
            </p>
          </div>
        </div>
      </div>

      <style>{`
        .calc-input {
          width: 100%;
          background: rgba(255,255,255,.06);
          border: 1px solid rgba(255,255,255,.14);
          border-radius: 4px;
          padding: 11px 14px;
          font-family: var(--fb);
          font-size: 14.5px;
          color: #fff;
          transition: border-color .15s;
          -webkit-appearance: none;
        }
        .calc-input:focus { outline: none; border-color: rgba(45,107,88,.8); }
        .calc-input option { background: #2c2a26; color: #fff; }
        @media (max-width: 960px) {
          .pain-grid-md { grid-template-columns: 1fr !important; gap: 48px !important; }
        }
      `}</style>
    </section>
  );
}

function CalcField({ label, children }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <label
        className="font-mono"
        style={{
          display: "block",
          fontSize: 11,
          letterSpacing: ".08em",
          textTransform: "uppercase",
          color: "rgba(255,255,255,.45)",
          marginBottom: 8,
        }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

function CalcRow({ label, value, tone, bold }) {
  const color = tone === "danger" ? "#FCA5A5" : tone === "safe" ? "#6EE7B7" : "#fff";
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        padding: "6px 0",
        fontSize: 14,
        color: "rgba(255,255,255,.65)",
        borderTop: bold ? "1px solid rgba(255,255,255,.1)" : "none",
        marginTop: bold ? 8 : 0,
        paddingTop: bold ? 14 : 6,
        fontWeight: bold ? 500 : 400,
      }}
    >
      <span>{label}</span>
      <span className="font-mono" style={{ fontSize: 15, color }}>
        {value}
      </span>
    </div>
  );
}
