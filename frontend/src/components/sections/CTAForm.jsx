import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { toast } from "sonner";
import { CheckCircle2, ArrowRight } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const SMARTCAPTCHA_SITE_KEY = process.env.REACT_APP_SMARTCAPTCHA_SITE_KEY || "";

const SERVERS = [
  { v: "1-3", label: "1–3 сервера" },
  { v: "4-10", label: "4–10 серверов" },
  { v: "11-30", label: "11–30 серверов" },
  { v: "30+", label: "Более 30" },
];

const TARIFFS = [
  { v: "undecided", label: "Не определился" },
  { v: "bronze", label: "Bronze" },
  { v: "silver", label: "Silver" },
  { v: "gold", label: "Gold" },
];

export default function CTAForm() {
  const [form, setForm] = useState({
    name: "",
    company: "",
    contact: "",
    email: "",
    servers: "",
    tariff: "undecided",
    message: "",
    consent: false,
    website: "", // honeypot — must stay empty
  });
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const [captchaToken, setCaptchaToken] = useState("");
  const captchaContainerRef = useRef(null);
  const captchaWidgetId = useRef(null);

  const onChange = (k) => (e) =>
    setForm((p) => ({
      ...p,
      [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value,
    }));

  // Sync tariff selection from Pricing section clicks
  useEffect(() => {
    const onPrefill = (e) => {
      if (e?.detail) {
        setForm((p) => ({ ...p, tariff: e.detail }));
      }
    };
    window.addEventListener("msp:set-tariff", onPrefill);
    return () => window.removeEventListener("msp:set-tariff", onPrefill);
  }, []);

  // Load Yandex SmartCaptcha (only if site key is configured)
  useEffect(() => {
    if (!SMARTCAPTCHA_SITE_KEY) return;
    if (document.getElementById("ya-smartcaptcha-script")) {
      tryRender();
      return;
    }
    const s = document.createElement("script");
    s.id = "ya-smartcaptcha-script";
    s.src = "https://smartcaptcha.yandexcloud.net/captcha.js";
    s.async = true;
    s.defer = true;
    s.onload = tryRender;
    document.head.appendChild(s);

    function tryRender() {
      // eslint-disable-next-line no-undef
      if (!window.smartCaptcha || !captchaContainerRef.current) return;
      if (captchaWidgetId.current !== null) return;
      // eslint-disable-next-line no-undef
      captchaWidgetId.current = window.smartCaptcha.render(
        captchaContainerRef.current,
        {
          sitekey: SMARTCAPTCHA_SITE_KEY,
          hl: "ru",
          callback: (token) => setCaptchaToken(token),
        }
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const resetCaptcha = () => {
    setCaptchaToken("");
    // eslint-disable-next-line no-undef
    if (window.smartCaptcha && captchaWidgetId.current !== null) {
      // eslint-disable-next-line no-undef
      window.smartCaptcha.reset(captchaWidgetId.current);
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.company.trim() || !form.contact.trim() || !form.servers) {
      toast.error("Пожалуйста, заполните обязательные поля");
      return;
    }
    if (!form.consent) {
      toast.error("Необходимо согласие на обработку персональных данных (152-ФЗ)");
      return;
    }
    if (SMARTCAPTCHA_SITE_KEY && !captchaToken) {
      toast.error("Подтвердите, что вы не робот");
      return;
    }

    setSending(true);
    try {
      const payload = {
        ...form,
        source: "landing",
        downtime_loss:
          document.querySelector('[data-testid="calc-result"] .font-mono:last-of-type')
            ?.textContent || null,
        smartcaptcha_token: captchaToken || undefined,
      };
      await axios.post(`${API}/leads`, payload);
      toast.success("Заявка отправлена — свяжемся в течение 2 часов");
      setDone(true);
    } catch (err) {
      const status = err?.response?.status;
      const msg = err?.response?.data?.detail || "Не удалось отправить. Попробуйте ещё раз.";
      if (status === 429) {
        toast.error("Слишком много попыток. Подождите минуту и попробуйте снова.");
      } else if (status === 400 || status === 422) {
        toast.error(typeof msg === "string" ? msg : "Проверьте введённые данные");
      } else {
        toast.error(typeof msg === "string" ? msg : "Ошибка сервера");
      }
      resetCaptcha();
    } finally {
      setSending(false);
    }
  };

  return (
    <section data-testid="cta-section" id="audit" style={{ padding: "104px 0" }}>
      <div className="wrap">
        <div
          className="cta-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 460px",
            gap: 80,
            alignItems: "start",
          }}
        >
          <div className="reveal">
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              Начать
            </div>
            <h2
              className="font-display"
              style={{
                fontSize: "clamp(38px, 4vw, 56px)",
                fontWeight: 400,
                letterSpacing: "-.02em",
                lineHeight: 1.08,
                marginBottom: 24,
                color: "var(--ink)",
              }}
            >
              Бесплатный
              <br />
              <em style={{ color: "var(--forest)", fontStyle: "italic" }}>
                экспресс-аудит
              </em>
              <br />
              за 30 минут
            </h2>
            <p
              style={{
                fontSize: 16,
                color: "var(--stone)",
                lineHeight: 1.75,
                marginBottom: 36,
                fontWeight: 300,
                maxWidth: 460,
              }}
            >
              Покажем конкретные риски вашей инфраструктуры и подберём
              оптимальный тариф. Онлайн, без обязательств, без продажи «в лоб» —
              только факты о вашей системе.
            </p>

            <ul
              style={{
                listStyle: "none",
                padding: 0,
                marginBottom: 40,
                borderTop: "1px solid var(--rule-lt)",
              }}
            >
              {[
                "Проверяем бэкапы: делаются, проверяются, восстанавливаются",
                "Смотрим открытые порты и доступы уволенных сотрудников",
                "Оцениваем дисковое пространство и прогноз заполнения",
                "Даём конкретные рекомендации и предварительный расчёт",
              ].map((t) => (
                <li
                  key={t}
                  style={{
                    display: "flex",
                    gap: 14,
                    alignItems: "baseline",
                    padding: "13px 0",
                    borderBottom: "1px solid var(--rule-lt)",
                    fontSize: 15,
                    color: "var(--ink)",
                  }}
                >
                  <ArrowRight
                    size={14}
                    color="var(--forest)"
                    style={{ flexShrink: 0 }}
                  />
                  {t}
                </li>
              ))}
            </ul>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 24,
              }}
            >
              {[
                ["30 мин", "длительность"],
                ["0 ₽", "стоимость"],
                ["≤ 2 ч", "до ответа"],
              ].map(([n, l]) => (
                <div key={l}>
                  <div
                    className="font-display"
                    style={{
                      fontSize: 32,
                      fontWeight: 500,
                      color: "var(--ink)",
                      lineHeight: 1,
                      marginBottom: 4,
                    }}
                  >
                    {n}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--stone-lt)" }}>{l}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Form */}
          <div className="reveal reveal-d2">
            <div
              data-testid="lead-form"
              style={{
                background: "#fff",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                padding: 32,
                boxShadow: "0 4px 32px rgba(26,24,21,.06)",
                position: "sticky",
                top: 88,
              }}
            >
              {done ? (
                <div data-testid="lead-form-success" style={{ textAlign: "center", padding: "32px 12px" }}>
                  <div
                    style={{
                      width: 56,
                      height: 56,
                      background: "var(--forest-dim)",
                      border: "1px solid var(--forest-bdr)",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      margin: "0 auto 20px",
                    }}
                  >
                    <CheckCircle2 size={22} color="var(--forest)" />
                  </div>
                  <div
                    className="font-display"
                    style={{
                      fontSize: 26,
                      fontWeight: 500,
                      marginBottom: 8,
                      letterSpacing: "-.01em",
                    }}
                  >
                    Заявка принята
                  </div>
                  <p
                    style={{
                      fontSize: 14,
                      color: "var(--stone)",
                      lineHeight: 1.65,
                      marginBottom: 20,
                    }}
                  >
                    Свяжемся в течение 2 часов в рабочее время.
                    <br />В нерабочее — утром следующего рабочего дня.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setDone(false);
                      setForm({
                        name: "",
                        company: "",
                        contact: "",
                        email: "",
                        servers: "",
                        tariff: "undecided",
                        message: "",
                        consent: false,
                        website: "",
                      });
                      resetCaptcha();
                    }}
                    className="btn-core btn-ghost"
                    data-testid="lead-form-reset"
                  >
                    Отправить ещё одну
                  </button>
                </div>
              ) : (
                <form onSubmit={onSubmit} noValidate>
                  <div
                    className="font-display"
                    style={{ fontSize: 24, fontWeight: 500, marginBottom: 4, letterSpacing: "-.01em" }}
                  >
                    Записаться на аудит
                  </div>
                  <p style={{ fontSize: 13, color: "var(--stone)", marginBottom: 22 }}>
                    Ответим в течение 2 часов в рабочее время
                  </p>

                  {/* Honeypot — hidden from humans, visible to bots */}
                  <div
                    aria-hidden="true"
                    style={{
                      position: "absolute",
                      left: "-9999px",
                      width: 1,
                      height: 1,
                      overflow: "hidden",
                    }}
                  >
                    <label htmlFor="website">Website (do not fill)</label>
                    <input
                      id="website"
                      name="website"
                      type="text"
                      tabIndex={-1}
                      autoComplete="off"
                      value={form.website}
                      onChange={onChange("website")}
                    />
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <Field label="Имя *">
                      <input
                        data-testid="f-name"
                        required
                        className="mspinput"
                        value={form.name}
                        onChange={onChange("name")}
                        placeholder="Иван Петров"
                      />
                    </Field>
                    <Field label="Компания *">
                      <input
                        data-testid="f-company"
                        required
                        className="mspinput"
                        value={form.company}
                        onChange={onChange("company")}
                        placeholder="ООО «Название»"
                      />
                    </Field>
                  </div>

                  <Field label="Телефон или Telegram *">
                    <input
                      data-testid="f-contact"
                      required
                      className="mspinput"
                      value={form.contact}
                      onChange={onChange("contact")}
                      placeholder="+7 (999) 123-45-67 или @username"
                    />
                  </Field>

                  <Field label="Email">
                    <input
                      data-testid="f-email"
                      type="email"
                      className="mspinput"
                      value={form.email}
                      onChange={onChange("email")}
                      placeholder="ivan@company.ru"
                    />
                  </Field>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <Field label="Количество серверов *">
                      <select
                        data-testid="f-servers"
                        required
                        id="f-servers-select"
                        className="mspinput"
                        value={form.servers}
                        onChange={onChange("servers")}
                      >
                        <option value="">Выберите…</option>
                        {SERVERS.map((s) => (
                          <option key={s.v} value={s.v}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Интересующий тариф">
                      <select
                        data-testid="f-tariff"
                        id="f-tariff"
                        className="mspinput"
                        value={form.tariff}
                        onChange={onChange("tariff")}
                      >
                        {TARIFFS.map((t) => (
                          <option key={t.v} value={t.v}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </Field>
                  </div>

                  <Field label="Комментарий">
                    <textarea
                      data-testid="f-msg"
                      rows={3}
                      className="mspinput"
                      value={form.message}
                      onChange={onChange("message")}
                      placeholder="Кратко: что есть, что беспокоит…"
                    />
                  </Field>

                  {/* Consent checkbox (152-ФЗ) */}
                  <label
                    style={{
                      display: "flex",
                      gap: 10,
                      alignItems: "flex-start",
                      margin: "8px 0 14px",
                      fontSize: 12.5,
                      color: "var(--stone)",
                      lineHeight: 1.55,
                      cursor: "pointer",
                    }}
                  >
                    <input
                      data-testid="f-consent"
                      type="checkbox"
                      checked={form.consent}
                      onChange={onChange("consent")}
                      required
                      style={{ marginTop: 3, flexShrink: 0 }}
                    />
                    <span>
                      Я согласен с{" "}
                      <a href="/docs/privacy.html" target="_blank" rel="noopener noreferrer" style={{ color: "var(--forest)", textDecoration: "underline" }}>
                        политикой обработки персональных данных
                      </a>{" "}
                      в соответствии с 152-ФЗ. Данные не передаются третьим лицам.
                    </span>
                  </label>

                  {SMARTCAPTCHA_SITE_KEY ? (
                    <div
                      ref={captchaContainerRef}
                      data-testid="smartcaptcha"
                      style={{ marginBottom: 14 }}
                    />
                  ) : null}

                  <button
                    type="submit"
                    disabled={sending}
                    data-testid="lead-form-submit"
                    className="btn-core btn-primary"
                    style={{ width: "100%", padding: 14, marginTop: 6, opacity: sending ? 0.6 : 1 }}
                  >
                    {sending ? "Отправка…" : "Получить бесплатный IT-аудит →"}
                  </button>
                  <p
                    style={{
                      fontSize: 11.5,
                      color: "var(--stone-lt)",
                      textAlign: "center",
                      marginTop: 12,
                      lineHeight: 1.6,
                    }}
                  >
                    Подробнее:{" "}
                    <a href="/docs/offer.html" target="_blank" rel="noopener noreferrer" style={{ color: "var(--stone)", textDecoration: "underline" }}>
                      оферта
                    </a>
                    {" · "}
                    <a href="/docs/sla.html" target="_blank" rel="noopener noreferrer" style={{ color: "var(--stone)", textDecoration: "underline" }}>
                      SLA
                    </a>
                  </p>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) {
          .cta-grid { grid-template-columns: 1fr !important; gap: 48px !important; }
        }
      `}</style>
    </section>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label
        className="font-mono"
        style={{
          display: "block",
          fontSize: 10.5,
          letterSpacing: ".1em",
          textTransform: "uppercase",
          color: "var(--stone)",
          marginBottom: 6,
        }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}
