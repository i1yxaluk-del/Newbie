## 2. Композитная воронка «визит → лид»

### Цели в интерфейсе Метрики (2025–2026)

В Метрике: **Настройка → Цели → Добавить цель**

Интерфейс цели:
- **Название** — отображается в отчётах
- **Избранная цель** ⭐ — показывать на главном дашборде
- **Тип условия** — выбор из списка
- **Условие** — зависит от типа (URL содержит/совпадает/начинается/регулярное выражение)
- **Доход** — RUB (опционально, для расчёта ROI)

### Типы целей (актуальные 2025–2026)

| Тип | Когда использовать | Нужен код |
|---|---|---|
| **Посещение страниц** | Просмотр /docs/sla, /docs/offer | ❌ Нет |
| **JavaScript-событие** | Клики, скроллы, кастомные события | ✅ Да, `reachGoal` |
| **Клик по кнопке** | CTA-кнопки (новый, 2025+) | ❌ Нет, через интерфейс |
| **Отправка формы** | Любая форма (новый, 2025+) | ❌ Нет, через интерфейс |
| **Клик на email** | `mailto:` ссылки | ❌ Нет |
| **Клик на телефон** | `tel:` ссылки | ❌ Нет |
| **Переход в мессенджер** | TG/WhatsApp кнопки | ❌ Нет |
| **Поиск по сайту** | Использование поиска | ❌ Нет |
| **Составная цель** | Воронка из нескольких шагов | ⚠️ Частично |
| **Продолжительность визита** | ≥ N минут на сайте | ❌ Нет |
| **Чат** | Данные из чат-виджета | ❌ Нет |

> **Примечание:** "Количество страниц" как отдельный тип убрали. Для глубины просмотра используйте метрику в отчётах или "Посещение страниц" с несколькими URL.

### Цели воронки (пошаговая настройка)

#### 1. visit_landing — автоматически
Создаётся само — любой визит = достижение.

#### 2. scroll_50 — JavaScript-событие
```
Название: scroll_50
Тип: JavaScript-событие
Идентификатор: scroll_50
Доход: 0
```

Код на лендинге:
```js
window.addEventListener('scroll', () => {
const scrolled = window.scrollY / (document.body.scrollHeight - window.innerHeight);
if (scrolled >= 0.5 && !window._scroll50Sent) {
  window._scroll50Sent = true;
  window.ym && window.ym(COUNTER_ID, 'reachGoal', 'scroll_50');
}
});
```

#### 3. scroll_pricing — JavaScript-событие
```
Название: scroll_pricing
Тип: JavaScript-событие
Идентификатор: scroll_pricing
```

Код:
```js
const pricing = document.querySelector('#pricing');
if (pricing) {
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting && !window._pricingSent) {
      window._pricingSent = true;
      window.ym && window.ym(COUNTER_ID, 'reachGoal', 'scroll_pricing');
    }
  });
}, { threshold: 0.5 });
observer.observe(pricing);
}
```

#### 4. cta_click — Клик по кнопке (НОВЫЙ, без кода)
```
Название: cta_click
Тип: Клик по кнопке
Условие: URL содержит /pricing или /contact
```

Или через JavaScript-событие (если нужна точность):
```
Тип: JavaScript-событие
Идентификатор: cta_click
```

```js
document.querySelectorAll('.btn-primary').forEach(btn => {
btn.addEventListener('click', () => {
  window.ym && window.ym(COUNTER_ID, 'reachGoal', 'cta_click');
});
});
```

#### 5. form_start — JavaScript-событие
```
Название: form_start
Тип: JavaScript-событие
Идентификатор: form_start
```

Код:
```js
document.querySelectorAll('form input').forEach(input => {
input.addEventListener('change', () => {
  if (!window._formStartSent) {
    window._formStartSent = true;
    window.ym && window.ym(COUNTER_ID, 'reachGoal', 'form_start');
  }
});
});
```

#### 6. form_submit — Отправка формы (НОВЫЙ, без кода) или JS
```
Название: form_submit
Тип: Отправка формы
Условие: URL содержит /api/leads
```

Или через JavaScript (после успешного fetch):
```
Тип: JavaScript-событие
Идентификатор: form_submit
```

```js
fetch('/api/leads', { method: 'POST', body: ... })
.then(res => {
  if (res.ok) {
    window.ym && window.ym(COUNTER_ID, 'reachGoal', 'form_submit');
  }
});
```

### Целевые CR по воронке

| Шаг | Цель | Целевой CR |
|---|---|---:|
| 1 | visit_landing | 100% (baseline) |
| 2 | scroll_50 | 60% |
| 3 | scroll_pricing | 35% |
| 4 | cta_click | 12% |
| 5 | form_start | 8% |
| 6 | form_submit | **3%** |

---

## 3. Цели-вспомогательные

### 3.1 Посещение страниц (без кода)

| Название | Тип | Условие | Зачем |
|---|---|---|---|
| doc_privacy_viewed | Посещение страниц | URL содержит `/docs/privacy` | evaluation signal |
| doc_sla_viewed | Посещение страниц | URL содержит `/docs/sla` | evaluation signal, hot |
| doc_offer_viewed | Посещение страниц | URL содержит `/docs/offer` | evaluation signal, hot |

### 3.2 JavaScript-события (нужен код)

| Название | Тип | Идентификатор | Код | Зачем |
|---|---|---|---|---|
| calc_completed | JavaScript-событие | `calc_completed` | `ym(..., 'reachGoal', 'calc_completed')` | engagement + intent |
| time_on_page_180 | Продолжительность визита | ≥ 180 сек | ❌ Без кода, в интерфейсе | high-engagement |
| form_field_error | JavaScript-событие | `form_field_error` | `ym(..., 'reachGoal', 'form_field_error')` | UX-проблема |
| lead_form_429 | JavaScript-событие | `lead_form_429` | `ym(..., 'reachGoal', 'lead_form_429')` | spam-атака |

> **time_on_page_180** — теперь тип "Продолжительность визита", не нужен код. Укажите 180 секунд в интерфейсе.

### 3.3 Клик по кнопке / Отправка формы (без кода, 2025+)

Если используете новые типы:
- **Клик по email** — отслеживает `mailto:` автоматически
- **Клик на телефон** — отслеживает `tel:` автоматически
- **Переход в мессенджер** — TG/WhatsApp кнопки