// Loader for landing.ru.json with optional localStorage override.
//
// Стратегия:
//   1. Дефолтный контент компилируется в bundle через import — мгновенный рендер.
//   2. На клиенте в localStorage может лежать "msp_landing_override" (полный JSON
//      или partial — deep-merge поверх дефолта). Это позволяет редактору
//      /admin/landing-edit показывать live-preview без пересборки.
//   3. Если override повреждён — silently fallback на default + console.warn.
//
// Совместимость: компоненты импортируют `useContent()` и читают любые поля
// — `nav`, `hero`, `pricing.plans[*]`, и т.д. Если редактор удалил поле
// — fallback на default обеспечивает безопасность.

import defaultContent from "./landing.ru.json";

const STORAGE_KEY = "msp_landing_override";

function isPlainObject(x) {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

// Deep-merge override into base. Arrays are REPLACED (not merged) so
// removing a plan/FAQ item works as expected.
export function mergeContent(base, override) {
  if (!override) return base;
  if (!isPlainObject(base) || !isPlainObject(override)) return override;
  const out = { ...base };
  for (const k of Object.keys(override)) {
    out[k] = mergeContent(base[k], override[k]);
  }
  return out;
}

function readOverride() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[content] override JSON corrupted, ignoring:", err.message);
    return null;
  }
}

let cached = null;

function getResolved() {
  if (cached) return cached;
  const override = readOverride();
  cached = mergeContent(defaultContent, override);
  return cached;
}

// Listen for live-edit events from the editor (same tab) and storage events
// (cross-tab) — reset cache so the next useContent() call returns fresh data.
if (typeof window !== "undefined") {
  const reset = () => {
    cached = null;
  };
  window.addEventListener("msp:content-changed", reset);
  window.addEventListener("storage", (e) => {
    if (e.key === STORAGE_KEY) reset();
  });
}

/**
 * Хук возвращает текущий контент — дефолт + override.
 * Не реактивный: компоненты должны полагаться на единый render-цикл.
 * Если редактор пишет в localStorage, он диспатчит msp:content-changed —
 * приложение само вызовет re-render через App.jsx (см. useContentRefreshKey).
 */
export function useContent() {
  return getResolved();
}

// Plain function for non-hook contexts (e.g. helpers, tests).
export function getContent() {
  return getResolved();
}

export { defaultContent };
