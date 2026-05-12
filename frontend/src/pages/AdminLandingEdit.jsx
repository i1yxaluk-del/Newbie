// Editor for landing.ru.json with JWT gate, live preview, and JSON download.
//
// Хранит рабочую копию контента в localStorage["msp_landing_override"], откуда
// её подхватывает useContent() при следующем рендере. После «Применить» лендинг
// в iframe-предпросмотре сразу показывает изменения. Кнопка «Скачать JSON»
// выдаёт файл, который нужно вручную закоммитить в репозиторий.
//
// Безопасность: страница доступна только за JWT (тот же токен, что у
// /admin/leads). Изменения не сохраняются на бэкенде — это инструмент
// предпросмотра + скачивания.

import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import defaultContent from "@/content/landing.ru.json";

const BACKEND = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
const API = `${BACKEND}/api`;

const STORAGE_TOKEN = "msp_admin_jwt";
const STORAGE_LEGACY = "msp_admin_token";
const STORAGE_OVERRIDE = "msp_landing_override";

function authHeaders() {
  const jwt = localStorage.getItem(STORAGE_TOKEN);
  if (jwt) return { Authorization: `Bearer ${jwt}` };
  const legacy = sessionStorage.getItem(STORAGE_LEGACY);
  if (legacy) return { "X-Admin-Token": legacy };
  return {};
}

function clearAuth() {
  localStorage.removeItem(STORAGE_TOKEN);
  sessionStorage.removeItem(STORAGE_LEGACY);
}

// Deep-clone via JSON — контент гарантированно сериализуем.
function clone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function readOverride() {
  try {
    const raw = localStorage.getItem(STORAGE_OVERRIDE);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function notifyContentChanged() {
  window.dispatchEvent(new Event("msp:content-changed"));
}

export default function AdminLandingEdit() {
  const [authed, setAuthed] = useState(false);
  const [password, setPassword] = useState("");
  const [loginPending, setLoginPending] = useState(false);
  const [diagnostic, setDiagnostic] = useState(null);

  // Auto-login if JWT is present.
  useEffect(() => {
    const headers = authHeaders();
    if (!Object.keys(headers).length) return;
    axios
      .get(`${API}/admin/whoami`, { headers })
      .then(() => setAuthed(true))
      .catch((err) => {
        if (err?.response?.status === 401) clearAuth();
      });
  }, []);

  const onLogin = async (e) => {
    e.preventDefault();
    if (!password) return;
    setLoginPending(true);
    setDiagnostic(null);
    try {
      const r = await axios.post(`${API}/admin/login`, { password });
      localStorage.setItem(STORAGE_TOKEN, r.data.token);
      toast.success("Вход выполнен");
      setPassword("");
      setAuthed(true);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        setDiagnostic("401: пароль не совпадает с ADMIN_TOKEN на сервере.");
        toast.error("Неверный пароль");
      } else {
        setDiagnostic(`HTTP ${status || "—"}: ${err.message}`);
        toast.error("Не удалось войти");
      }
    } finally {
      setLoginPending(false);
    }
  };

  if (!authed) {
    return (
      <LoginScreen
        password={password}
        setPassword={setPassword}
        onSubmit={onLogin}
        pending={loginPending}
        diagnostic={diagnostic}
      />
    );
  }
  return <Editor />;
}

function LoginScreen({ password, setPassword, onSubmit, pending, diagnostic }) {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "var(--cream)",
        padding: 24,
      }}
    >
      <form
        onSubmit={onSubmit}
        style={{
          background: "#fff",
          border: "1px solid var(--rule)",
          borderRadius: 10,
          padding: 32,
          maxWidth: 380,
          width: "100%",
        }}
      >
        <h1
          style={{
            fontFamily: "var(--fd)",
            fontSize: 22,
            fontWeight: 500,
            margin: "0 0 6px",
            color: "var(--ink)",
          }}
        >
          Редактор лендинга
        </h1>
        <p
          style={{
            fontSize: 13,
            color: "var(--stone)",
            margin: "0 0 22px",
            lineHeight: 1.5,
          }}
        >
          Тот же пароль, что у{" "}
          <Link to="/admin/leads" style={{ color: "var(--forest)" }}>
            /admin/leads
          </Link>
          .
        </p>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Пароль администратора"
          autoFocus
          style={{
            width: "100%",
            padding: "11px 14px",
            border: "1px solid var(--rule)",
            borderRadius: 6,
            fontSize: 14,
            fontFamily: "var(--fm)",
            background: "var(--cream)",
            color: "var(--ink)",
            marginBottom: 14,
          }}
        />
        {diagnostic && (
          <div
            style={{
              fontSize: 12,
              color: "#a33",
              background: "rgba(170,40,40,.06)",
              padding: "8px 10px",
              borderRadius: 4,
              marginBottom: 14,
              lineHeight: 1.5,
            }}
          >
            {diagnostic}
          </div>
        )}
        <button
          type="submit"
          disabled={pending || !password}
          className="btn-core btn-primary"
          style={{ width: "100%" }}
        >
          {pending ? "Вход…" : "Войти"}
        </button>
      </form>
    </main>
  );
}

function Editor() {
  // Working copy in component state. On mount: hydrate from localStorage if
  // override exists, otherwise clone defaultContent.
  const [draft, setDraft] = useState(() => {
    const override = readOverride();
    return override || clone(defaultContent);
  });
  const [dirty, setDirty] = useState(() => !!readOverride());
  const iframeRef = useRef(null);

  // Whenever draft changes — write to localStorage immediately, but
  // debounce the iframe reload (500 ms) so что rapid typing не моргает.
  useEffect(() => {
    localStorage.setItem(STORAGE_OVERRIDE, JSON.stringify(draft));
    notifyContentChanged();
    setDirty(true);
    const t = setTimeout(() => {
      if (iframeRef.current) {
        try {
          iframeRef.current.contentWindow.location.reload();
        } catch {
          /* ignored */
        }
      }
    }, 500);
    return () => clearTimeout(t);
  }, [draft]);

  const onReset = () => {
    if (!window.confirm("Сбросить все правки и вернуться к репозиторному JSON?")) return;
    localStorage.removeItem(STORAGE_OVERRIDE);
    setDraft(clone(defaultContent));
    setDirty(false);
    notifyContentChanged();
    if (iframeRef.current) {
      iframeRef.current.contentWindow.location.reload();
    }
    toast.success("Откат выполнен — показан исходный JSON из репозитория");
  };

  const onDownload = () => {
    // Strip $schema and _comment from output? Keep them so the file matches
    // repo file exactly.
    const blob = new Blob([JSON.stringify(draft, null, 2) + "\n"], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "landing.ru.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("landing.ru.json скачан. Закоммитьте файл в frontend/src/content/");
  };

  const onLogout = () => {
    clearAuth();
    window.location.href = "/admin/landing-edit";
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "minmax(420px, 36%) 1fr",
        background: "var(--cream)",
      }}
    >
      <aside
        style={{
          borderRight: "1px solid var(--rule)",
          padding: "24px 24px 40px",
          overflowY: "auto",
          maxHeight: "100vh",
          background: "#fff",
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 18,
            paddingBottom: 14,
            borderBottom: "1px solid var(--rule-lt)",
          }}
        >
          <div>
            <div
              style={{
                fontFamily: "var(--fd)",
                fontSize: 18,
                fontWeight: 500,
                color: "var(--ink)",
              }}
            >
              Редактор лендинга
            </div>
            <div style={{ fontSize: 12, color: "var(--stone)" }}>
              {dirty ? "● Есть несохранённые правки" : "Совпадает с репозиторием"}
            </div>
          </div>
          <button
            onClick={onLogout}
            className="btn-core btn-ghost"
            style={{ fontSize: 12, padding: "6px 10px" }}
          >
            Выйти
          </button>
        </header>

        <div
          style={{
            display: "flex",
            gap: 8,
            marginBottom: 22,
            flexWrap: "wrap",
          }}
        >
          <button
            onClick={onDownload}
            className="btn-core btn-primary"
            style={{ padding: "10px 16px", fontSize: 13.5 }}
          >
            Скачать landing.ru.json
          </button>
          <button
            onClick={onReset}
            className="btn-core btn-ghost"
            style={{ padding: "10px 16px", fontSize: 13.5 }}
          >
            Сбросить правки
          </button>
        </div>

        <div
          style={{
            background: "var(--cream)",
            border: "1px solid var(--rule-lt)",
            borderRadius: 6,
            padding: "10px 12px",
            fontSize: 11.5,
            color: "var(--stone)",
            lineHeight: 1.55,
            marginBottom: 20,
          }}
        >
          После «Скачать» поместите файл в{" "}
          <code style={{ background: "rgba(0,0,0,.05)", padding: "1px 4px" }}>
            frontend/src/content/landing.ru.json
          </code>{" "}
          и закоммитьте — изменения применятся для всех посетителей после
          следующего деплоя. До этого правки видны только в текущем браузере.
        </div>

        <Sections draft={draft} setDraft={setDraft} />
      </aside>

      <section
        style={{
          position: "sticky",
          top: 0,
          maxHeight: "100vh",
          overflow: "hidden",
          background: "var(--cream-deep)",
        }}
      >
        <div
          style={{
            height: 44,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 16px",
            background: "#fff",
            borderBottom: "1px solid var(--rule)",
            fontSize: 12.5,
            color: "var(--stone)",
            fontFamily: "var(--fm)",
          }}
        >
          <span>preview · / (override активен)</span>
          <a
            href="/"
            target="_blank"
            rel="noreferrer"
            style={{ color: "var(--forest)", textDecoration: "none" }}
          >
            Открыть в новой вкладке ↗
          </a>
        </div>
        <iframe
          ref={iframeRef}
          src="/"
          title="landing-preview"
          style={{ width: "100%", height: "calc(100vh - 44px)", border: 0, background: "var(--cream)" }}
        />
      </section>
    </main>
  );
}

// ---------- form sections ----------

function Sections({ draft, setDraft }) {
  const setField = (path, value) => {
    setDraft((prev) => {
      const next = clone(prev);
      const keys = path.split(".");
      let cursor = next;
      for (let i = 0; i < keys.length - 1; i++) {
        cursor = cursor[keys[i]];
      }
      cursor[keys[keys.length - 1]] = value;
      return next;
    });
  };
  const updateArray = (path, idx, key, value) => {
    setDraft((prev) => {
      const next = clone(prev);
      const keys = path.split(".");
      let cursor = next;
      for (const k of keys) cursor = cursor[k];
      cursor[idx][key] = value;
      return next;
    });
  };

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <SectionBlock title="Hero — первый экран" defaultOpen>
        <Field label="Заголовок (часть 1)">
          <Textarea
            value={draft.hero.h1Before}
            onChange={(v) => setField("hero.h1Before", v)}
          />
        </Field>
        <Field label="Заголовок (курсивная часть)">
          <Textarea
            value={draft.hero.h1Em}
            onChange={(v) => setField("hero.h1Em", v)}
          />
        </Field>
        <Field label="Лид-абзац">
          <Textarea
            value={draft.hero.lead}
            onChange={(v) => setField("hero.lead", v)}
            rows={3}
          />
        </Field>
        <CtaPair
          cta={draft.hero.ctaPrimary}
          onChange={(v) => setField("hero.ctaPrimary", v)}
          label="Primary CTA"
        />
        <CtaPair
          cta={draft.hero.ctaSecondary}
          onChange={(v) => setField("hero.ctaSecondary", v)}
          label="Secondary CTA"
        />
      </SectionBlock>

      <SectionBlock title="Trust-strip — иконки сервисов и инструментов">
        <Field label="Подпись над услугами">
          <Input
            value={draft.trust.servicesLabel}
            onChange={(v) => setField("trust.servicesLabel", v)}
          />
        </Field>
        <Field label="Подпись над инструментами">
          <Input
            value={draft.trust.toolsLabel}
            onChange={(v) => setField("trust.toolsLabel", v)}
          />
        </Field>
        <div style={{ marginTop: 8 }}>
          <strong style={subhead}>Что обслуживаем</strong>
          {draft.trust.services.map((it, i) => (
            <div key={i} style={inlineRow}>
              <Input
                value={it.icon}
                onChange={(v) => updateArray("trust.services", i, "icon", v)}
                placeholder="icon"
                style={{ flex: "0 0 110px" }}
              />
              <Input
                value={it.label}
                onChange={(v) => updateArray("trust.services", i, "label", v)}
                placeholder="label"
              />
            </div>
          ))}
        </div>
        <div style={{ marginTop: 14 }}>
          <strong style={subhead}>Чем обслуживаем</strong>
          {draft.trust.tools.map((it, i) => (
            <div key={i} style={inlineRow}>
              <Input
                value={it.icon}
                onChange={(v) => updateArray("trust.tools", i, "icon", v)}
                placeholder="icon"
                style={{ flex: "0 0 110px" }}
              />
              <Select
                value={it.kind || "service"}
                onChange={(v) => updateArray("trust.tools", i, "kind", v)}
                options={["service", "oss", "ru"]}
                style={{ flex: "0 0 80px" }}
              />
              <Input
                value={it.label}
                onChange={(v) => updateArray("trust.tools", i, "label", v)}
                placeholder="label"
              />
            </div>
          ))}
        </div>
        <p style={{ ...hintStyle, marginTop: 8 }}>
          Имена иконок — см. <code>docs/EDITING.md → Иконки</code>.
        </p>
      </SectionBlock>

      <SectionBlock title="Capabilities — пилоны (4 шт.)">
        <Field label="Заголовок · часть 1">
          <Input
            value={draft.capabilities.headingFirst}
            onChange={(v) => setField("capabilities.headingFirst", v)}
          />
        </Field>
        <Field label="Заголовок · курсив">
          <Input
            value={draft.capabilities.headingEm}
            onChange={(v) => setField("capabilities.headingEm", v)}
          />
        </Field>
        <Field label="Заголовок · часть 2">
          <Input
            value={draft.capabilities.headingLast}
            onChange={(v) => setField("capabilities.headingLast", v)}
          />
        </Field>
        {draft.capabilities.panels.map((p, i) => (
          <div key={p.id} style={cardStyle}>
            <strong style={subhead}>
              {p.tab} · <span style={{ color: "var(--stone)" }}>{p.id}</span>
            </strong>
            <Field label="Tab label">
              <Input
                value={p.tab}
                onChange={(v) => updateArray("capabilities.panels", i, "tab", v)}
              />
            </Field>
            <Field label="Title">
              <Input
                value={p.title}
                onChange={(v) => updateArray("capabilities.panels", i, "title", v)}
              />
            </Field>
            <Field label="Em (курсив)">
              <Input
                value={p.em}
                onChange={(v) => updateArray("capabilities.panels", i, "em", v)}
              />
            </Field>
            <Field label="Bullets">
              {p.bullets.map((b, bi) => (
                <Textarea
                  key={bi}
                  value={b}
                  onChange={(v) => {
                    setDraft((prev) => {
                      const next = clone(prev);
                      next.capabilities.panels[i].bullets[bi] = v;
                      return next;
                    });
                  }}
                  rows={2}
                />
              ))}
            </Field>
          </div>
        ))}
      </SectionBlock>

      <SectionBlock title="Pricing — тарифы (3 шт.)">
        <Field label="Eyebrow">
          <Input
            value={draft.pricing.eyebrow}
            onChange={(v) => setField("pricing.eyebrow", v)}
          />
        </Field>
        <Field label="Заголовок · часть 1">
          <Input
            value={draft.pricing.headingBefore}
            onChange={(v) => setField("pricing.headingBefore", v)}
          />
        </Field>
        <Field label="Заголовок · курсив">
          <Input
            value={draft.pricing.headingEm}
            onChange={(v) => setField("pricing.headingEm", v)}
          />
        </Field>
        <Field label="Лид">
          <Textarea
            value={draft.pricing.lead}
            onChange={(v) => setField("pricing.lead", v)}
            rows={2}
          />
        </Field>
        {draft.pricing.plans.map((plan, i) => (
          <div key={plan.id} style={cardStyle}>
            <strong style={subhead}>
              {plan.name} · {plan.id}
            </strong>
            <Field label="Eyebrow">
              <Input
                value={plan.eyebrow}
                onChange={(v) => updateArray("pricing.plans", i, "eyebrow", v)}
              />
            </Field>
            <Field label="Название">
              <Input
                value={plan.name}
                onChange={(v) => updateArray("pricing.plans", i, "name", v)}
              />
            </Field>
            <Field label="Подпись">
              <Input
                value={plan.tagline}
                onChange={(v) => updateArray("pricing.plans", i, "tagline", v)}
              />
            </Field>
            <Field label="Цена (без ₽)">
              <Input
                value={plan.price}
                onChange={(v) => updateArray("pricing.plans", i, "price", v)}
              />
            </Field>
            <Field label="Стоимость запуска">
              <Input
                value={plan.setup}
                onChange={(v) => updateArray("pricing.plans", i, "setup", v)}
              />
            </Field>
            <Field label="Лимит">
              <Input
                value={plan.limit}
                onChange={(v) => updateArray("pricing.plans", i, "limit", v)}
              />
            </Field>
            <Field label="CTA-подпись">
              <Input
                value={plan.cta}
                onChange={(v) => updateArray("pricing.plans", i, "cta", v)}
              />
            </Field>
            <Field label="Featured (выделен)">
              <Select
                value={plan.featured ? "true" : "false"}
                onChange={(v) =>
                  updateArray("pricing.plans", i, "featured", v === "true")
                }
                options={["false", "true"]}
              />
            </Field>
            <Field label="Фичи">
              {plan.features.map((f, fi) => (
                <div key={fi} style={inlineRow}>
                  <Input
                    value={f.text}
                    onChange={(v) => {
                      setDraft((prev) => {
                        const next = clone(prev);
                        next.pricing.plans[i].features[fi].text = v;
                        return next;
                      });
                    }}
                  />
                  <Select
                    value={f.bold ? "bold" : "norm"}
                    onChange={(v) => {
                      setDraft((prev) => {
                        const next = clone(prev);
                        next.pricing.plans[i].features[fi].bold = v === "bold";
                        return next;
                      });
                    }}
                    options={["norm", "bold"]}
                    style={{ flex: "0 0 80px" }}
                  />
                </div>
              ))}
            </Field>
          </div>
        ))}
      </SectionBlock>

      <SectionBlock title="Process — шаги онбординга">
        <Field label="Eyebrow">
          <Input
            value={draft.process.eyebrow}
            onChange={(v) => setField("process.eyebrow", v)}
          />
        </Field>
        <Field label="Заголовок · часть 1">
          <Input
            value={draft.process.headingBefore}
            onChange={(v) => setField("process.headingBefore", v)}
          />
        </Field>
        <Field label="Заголовок · курсив">
          <Input
            value={draft.process.headingEm}
            onChange={(v) => setField("process.headingEm", v)}
          />
        </Field>
        <Field label="Заголовок · после">
          <Input
            value={draft.process.headingAfter}
            onChange={(v) => setField("process.headingAfter", v)}
          />
        </Field>
        <Field label="Лид">
          <Textarea
            value={draft.process.lead}
            onChange={(v) => setField("process.lead", v)}
            rows={2}
          />
        </Field>
        {draft.process.steps.map((s, i) => (
          <div key={i} style={cardStyle}>
            <Field label="Дата (День 0 / …)">
              <Input
                value={s.date}
                onChange={(v) => updateArray("process.steps", i, "date", v)}
              />
            </Field>
            <Field label="Заголовок шага">
              <Input
                value={s.title}
                onChange={(v) => updateArray("process.steps", i, "title", v)}
              />
            </Field>
            <Field label="Описание">
              <Textarea
                value={s.desc}
                onChange={(v) => updateArray("process.steps", i, "desc", v)}
                rows={4}
              />
            </Field>
          </div>
        ))}
      </SectionBlock>

      <SectionBlock title="Pain + калькулятор простоя">
        <Field label="Eyebrow">
          <Input
            value={draft.pain.eyebrow}
            onChange={(v) => setField("pain.eyebrow", v)}
          />
        </Field>
        <Field label="Заголовок · часть 1">
          <Input
            value={draft.pain.headingBefore}
            onChange={(v) => setField("pain.headingBefore", v)}
          />
        </Field>
        <Field label="Заголовок · курсив">
          <Input
            value={draft.pain.headingEm}
            onChange={(v) => setField("pain.headingEm", v)}
          />
        </Field>
        <Field label="Лид">
          <Textarea
            value={draft.pain.lead}
            onChange={(v) => setField("pain.lead", v)}
          />
        </Field>
        <Field label="Pain-bullets">
          {draft.pain.points.map((p, i) => (
            <Textarea
              key={i}
              value={p}
              onChange={(v) => {
                setDraft((prev) => {
                  const next = clone(prev);
                  next.pain.points[i] = v;
                  return next;
                });
              }}
              rows={2}
            />
          ))}
        </Field>
        <Field label="Заголовок калькулятора">
          <Input
            value={draft.pain.calcTitle}
            onChange={(v) => setField("pain.calcTitle", v)}
          />
        </Field>
        <Field label="Подзаголовок калькулятора">
          <Input
            value={draft.pain.calcLead}
            onChange={(v) => setField("pain.calcLead", v)}
          />
        </Field>
        <Field label="Годовая стоимость Bronze (₽, для сравнения)">
          <Input
            value={String(draft.pain.bronzeAnnualPrice)}
            onChange={(v) =>
              setField("pain.bronzeAnnualPrice", Number(v.replace(/\D/g, "")) || 0)
            }
          />
        </Field>
      </SectionBlock>

      <SectionBlock title="FAQ — вопросы и ответы">
        <Field label="Eyebrow">
          <Input
            value={draft.faq.eyebrow}
            onChange={(v) => setField("faq.eyebrow", v)}
          />
        </Field>
        <Field label="Заголовок · часть 1">
          <Input
            value={draft.faq.headingBefore}
            onChange={(v) => setField("faq.headingBefore", v)}
          />
        </Field>
        <Field label="Заголовок · курсив">
          <Input
            value={draft.faq.headingEm}
            onChange={(v) => setField("faq.headingEm", v)}
          />
        </Field>
        {draft.faq.items.map((it, i) => (
          <div key={i} style={cardStyle}>
            <Field label={`Вопрос #${i + 1}`}>
              <Textarea
                value={it.q}
                onChange={(v) => updateArray("faq.items", i, "q", v)}
                rows={2}
              />
            </Field>
            <Field label="Ответ">
              <Textarea
                value={it.a}
                onChange={(v) => updateArray("faq.items", i, "a", v)}
                rows={5}
              />
            </Field>
          </div>
        ))}
      </SectionBlock>

      <SectionBlock title="Final CTA — финальный блок">
        <Field label="Eyebrow">
          <Input
            value={draft.finalCta.eyebrow}
            onChange={(v) => setField("finalCta.eyebrow", v)}
          />
        </Field>
        <Field label="Заголовок · часть 1">
          <Textarea
            value={draft.finalCta.headingBefore}
            onChange={(v) => setField("finalCta.headingBefore", v)}
            rows={2}
          />
        </Field>
        <Field label="Заголовок · курсив">
          <Input
            value={draft.finalCta.headingEm}
            onChange={(v) => setField("finalCta.headingEm", v)}
          />
        </Field>
        <Field label="Лид">
          <Textarea
            value={draft.finalCta.lead}
            onChange={(v) => setField("finalCta.lead", v)}
            rows={2}
          />
        </Field>
        <CtaPair
          cta={draft.finalCta.ctaPrimary}
          onChange={(v) => setField("finalCta.ctaPrimary", v)}
          label="Primary CTA"
        />
        <CtaPair
          cta={draft.finalCta.ctaSecondary}
          onChange={(v) => setField("finalCta.ctaSecondary", v)}
          label="Secondary CTA"
        />
        <Field label="Compliance-бейджи">
          {draft.finalCta.badges.map((b, i) => (
            <Input
              key={i}
              value={b}
              onChange={(v) => {
                setDraft((prev) => {
                  const next = clone(prev);
                  next.finalCta.badges[i] = v;
                  return next;
                });
              }}
            />
          ))}
        </Field>
      </SectionBlock>

      <SectionBlock title="Nav + Footer + Brand">
        <Field label="Бренд · название">
          <Input
            value={draft.meta.brand.name}
            onChange={(v) => setField("meta.brand.name", v)}
          />
        </Field>
        <Field label="Бренд · акцентная часть (зелёная)">
          <Input
            value={draft.meta.brand.accent}
            onChange={(v) => setField("meta.brand.accent", v)}
          />
        </Field>
        <Field label="Nav CTA">
          <Input
            value={draft.nav.cta.label}
            onChange={(v) => setField("nav.cta.label", v)}
          />
        </Field>
        <Field label="Tagline в подвале">
          <Textarea
            value={draft.footer.tagline}
            onChange={(v) => setField("footer.tagline", v)}
            rows={2}
          />
        </Field>
        <Field label="Реквизиты ИП (одной строкой)">
          <Input
            value={draft.footer.legal}
            onChange={(v) => setField("footer.legal", v)}
          />
        </Field>
        <Field label="Email">
          <Input
            value={draft.footer.email}
            onChange={(v) => setField("footer.email", v)}
          />
        </Field>
        <Field label="Telegram · ссылка">
          <Input
            value={draft.footer.telegram.href}
            onChange={(v) => setField("footer.telegram.href", v)}
          />
        </Field>
        <Field label="Telegram · подпись">
          <Input
            value={draft.footer.telegram.label}
            onChange={(v) => setField("footer.telegram.label", v)}
          />
        </Field>
      </SectionBlock>
    </div>
  );
}

// ---------- shared inputs ----------

function SectionBlock({ title, children, defaultOpen }) {
  const [open, setOpen] = useState(!!defaultOpen);
  return (
    <details
      open={open}
      onToggle={(e) => setOpen(e.target.open)}
      style={{
        border: "1px solid var(--rule)",
        borderRadius: 6,
        padding: "10px 14px",
        background: "var(--cream)",
      }}
    >
      <summary
        style={{
          cursor: "pointer",
          fontFamily: "var(--fd)",
          fontSize: 14,
          fontWeight: 500,
          color: "var(--ink)",
          listStyle: "revert",
          padding: "4px 0",
        }}
      >
        {title}
      </summary>
      <div style={{ display: "grid", gap: 12, marginTop: 12 }}>{children}</div>
    </details>
  );
}

function Field({ label, children }) {
  return (
    <label style={{ display: "grid", gap: 5 }}>
      <span
        style={{
          fontFamily: "var(--fm)",
          fontSize: 10.5,
          letterSpacing: ".06em",
          textTransform: "uppercase",
          color: "var(--stone)",
        }}
      >
        {label}
      </span>
      {children}
    </label>
  );
}

function Input({ value, onChange, placeholder, style }) {
  return (
    <input
      type="text"
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      style={{ ...inputStyle, ...style }}
    />
  );
}

function Textarea({ value, onChange, rows = 2, placeholder }) {
  return (
    <textarea
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      rows={rows}
      placeholder={placeholder}
      style={{ ...inputStyle, resize: "vertical", minHeight: rows * 22, lineHeight: 1.4 }}
    />
  );
}

function Select({ value, onChange, options, style }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ ...inputStyle, ...style }}
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

function CtaPair({ cta, onChange, label }) {
  return (
    <div style={{ display: "grid", gap: 6 }}>
      <span
        style={{
          fontFamily: "var(--fm)",
          fontSize: 10.5,
          letterSpacing: ".06em",
          textTransform: "uppercase",
          color: "var(--stone)",
        }}
      >
        {label}
      </span>
      <div style={inlineRow}>
        <Input
          value={cta.label}
          onChange={(v) => onChange({ ...cta, label: v })}
          placeholder="Текст кнопки"
        />
        <Input
          value={cta.href}
          onChange={(v) => onChange({ ...cta, href: v })}
          placeholder="Ссылка"
          style={{ flex: "0 0 160px" }}
        />
      </div>
    </div>
  );
}

const inputStyle = {
  width: "100%",
  padding: "8px 11px",
  border: "1px solid var(--rule)",
  borderRadius: 5,
  fontSize: 13.5,
  fontFamily: "var(--fb)",
  background: "#fff",
  color: "var(--ink)",
  boxSizing: "border-box",
};
const inlineRow = {
  display: "flex",
  gap: 6,
  alignItems: "stretch",
  marginBottom: 6,
};
const subhead = {
  display: "block",
  fontFamily: "var(--fm)",
  fontSize: 10.5,
  letterSpacing: ".06em",
  textTransform: "uppercase",
  color: "var(--ink)",
  marginBottom: 6,
};
const cardStyle = {
  border: "1px solid var(--rule-lt)",
  borderRadius: 5,
  padding: "10px 12px",
  background: "#fff",
  display: "grid",
  gap: 10,
};
const hintStyle = {
  fontSize: 11.5,
  color: "var(--stone)",
  lineHeight: 1.5,
  margin: 0,
};
