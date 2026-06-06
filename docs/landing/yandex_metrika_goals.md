# Цели Яндекс.Метрики — настройка (2025–2026)

> Все цели должны быть настроены в Метрике **до первой платной
> рекламной кампании**. Иначе у нас нет data для оптимизации.

---

## 1. Создание счетчика (новый интерфейс, 2025+)

### Шаг 1 — Добавить счетчик

metrika.yandex.ru → «Добавить счетчик»

**Поля:**

| Поле | Что вводить | Пример |
|---|---|---|
| **Имя счетчика** | Любое название для списка | `MSPShield landing` |
| **Адрес сайта** | Домен без `http://` | `msp-claude.online` |
| **Часовой пояс** | Europe/Moscow (UTC+3) | `Москва` |
| **Валюта** | Для e-com (если будет) | `RUB` |

**Дополнительные настройки** (раскрыть стрелку):
- ✅ Вебвизор, карта скроллинга, аналитика форм
- ✅ Включая поддомены (если есть `www.` или `blog.`)
- ❌ Не сохранять полные IP-адреса (GDPR/152-ФЗ)
- ❌ Принимать данные только с указанных адресов (если домен фиксирован)

→ **Продолжить**

### Шаг 2 — Профиль сайта (новый, с 22.07.2025)

Метрика предложит заполнить профиль:

| Поле | Выбор |
|---|---|
| **Тип сайта** | B2B / Лидогенерация |
| **Индустрия** | IT / Информационная безопасность |
| **CMS** | Custom (React) |
| **CRM** | Kaiten / Custom |
| **Ваши роли** | Маркетолог, Разработчик, Аналитик |

На основе профиля Метрика подберёт рекомендуемые дашборды и цели.
**Можно пропустить** — всё настраивается вручную ниже.

### Шаг 3 — Установка кода

В интерфейсе Метрики: **Настройка → Счетчик → Способ установки**

Доступные варианты:

| Вариант | Когда выбирать | Для MSPShield |
|---|---|---|
| **HTML, CMS и конструкторы** | Статический сайт или SSR (Next.js) | ❌ Не наш случай |
| **Управление тегами** | Через Google Tag Manager / Yandex TMS | ⚠️ Можно, но лишняя зависимость |
| **SPA** | React, Vue, Angular — ручная инициализация | ✅ **Наш случай** |

#### Для React (SPA-вариант)

```js
// В корневом компоненте (App.jsx или index.js)
import { useEffect } from 'react';

const YM_COUNTER_ID = process.env.REACT_APP_YM_COUNTER_ID;

function initYM() {
if (window.ym) return;

(function(m,e,t,r,i,k,a){
  m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
  m[i].l=1*new Date();
  k=e.createElement(t),a=e.getElementsByTagName(t)[0];
  k.async=1;k.src=r;a.parentNode.insertBefore(k,a)
})(window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");

ym(YM_COUNTER_ID, "init", {
  clickmap: true,
  trackLinks: true,
  accurateTrackBounce: true,
  webvisor: true,
  trackHash: true,        // Отслеживать hash-изменения (React Router)
  ecommerce: "dataLayer", // Для e-com целей (опционально)
});
}

// В App.jsx
useEffect(() => {
initYM();
}, []);
```

#### Альтернатива: react-yandex-metrika

```bash
npm install react-yandex-metrika
```

```js
import { YMInitializer } from 'react-yandex-metrika';

// В App.jsx
<YMInitializer
accounts={[YM_COUNTER_ID]}
options={{
  clickmap: true,
  trackLinks: true,
  accurateTrackBounce: true,
  webvisor: true,
  trackHash: true,
}}
version="2"
/>
```

#### Для SSR (Next.js)

```js
// pages/_app.js или app/layout.tsx
import Script from 'next/script';

<Script
id="yandex-metrika"
strategy="afterInteractive"
dangerouslySetInnerHTML={{
  __html: `
    (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
    m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0];k.async=1;k.src=r;a.parentNode.insertBefore(k,a)})
    (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
    ym(${YM_COUNTER_ID}, "init", {clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true,trackHash:true});
  `
}}
/>
```

#### Проверка установки

```js
// В консоли браузера
ym(YM_COUNTER_ID, 'reachGoal', 'test_goal');
// Должно вернуть undefined без ошибок
```

---

## 2. Композитная воронка «визит → лид»

### Интерфейс создания цели (2025–2026)

В Метрике: **Настройка → Цели → Добавить цель**

Поля в форме:

| Поле | Описание |
|---|---|
| **Название** | Отображается в отчётах и дашборде |
| **Избранная цель** ⭐ | Показывать на главном дашборде |
| **Тип условия** | Выбор из списка (см. ниже) |
| **Условие** | Зависит от типа (URL содержит / совпадает / начинается / регулярное выражение) |
| **Доход** | RUB — опционально, для расчёта ROI |

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
| **Продолжительность визита** | ≥ N минут на сайте (2025+) | ❌ Нет |
| **Чат** | Данные из чат-виджета (2025+) | ❌ Нет |

> **Примечание:** "Количество страниц" как отдельный тип убрали. Для глубины просмотра используйте метрику в отчётах или "Посещение страниц" с несколькими URL.

### Цели воронки (пошаговая настройка)

#### 1. visit_landing — автоматически
Создаётся само — любой визит = достижение.

#### 2. scroll_50 — JavaScript-событие
```
Название: scroll_50
Избранная цель: ⭐ (да)
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
Избранная цель: ⭐ (да)
Тип: JavaScript-событие
Идентификатор: scroll_pricing
Доход: 0
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

#### 4. cta_click — Клик по кнопке (НОВЫЙ, без кода) или JavaScript-событие

**Вариант А — Клик по кнопке (без кода, 2025+):**
```
Название: cta_click
Избранная цель: ⭐ (да)
Тип: Клик по кнопке
Условие: URL содержит /pricing или /contact
Доход: 0
```

**Вариант Б — JavaScript-событие (точнее, если кнопки динамические):**
```
Название: cta_click
Тип: JavaScript-событие
Идентификатор: cta_click
Доход: 0
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
Доход: 0
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

#### 6. form_submit — Отправка формы (НОВЫЙ, без кода) или JavaScript-событие

**Вариант А — Отправка формы (без кода, 2025+):**
```
Название: form_submit
Избранная цель: ⭐ (да)
Тип: Отправка формы
Условие: URL содержит /api/leads
Доход: 0
```

**Вариант Б — JavaScript-событие (после успешного fetch):**
```
Название: form_submit
Тип: JavaScript-событие
Идентификатор: form_submit
Доход: 0
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
| form_field_error | JavaScript-событие | `form_field_error` | `ym(..., 'reachGoal', 'form_field_error')` | UX-проблема |
| lead_form_429 | JavaScript-событие | `lead_form_429` | `ym(..., 'reachGoal', 'lead_form_429')` | spam-атака |

### 3.3 Продолжительность визита (без кода, 2025+)

```
Название: time_on_page_180
Тип: Продолжительность визита
≥ 180 секунд
Доход: 0
```

> Раньше это был JavaScript-событие. Теперь отдельный тип — не нужен код.

### 3.4 Клик по кнопке / Отправка формы (без кода, 2025+)

Если используете новые типы:
- **Клик по email** — отслеживает `mailto:` автоматически
- **Клик на телефон** — отслеживает `tel:` автоматически
- **Переход в мессенджер** — TG/WhatsApp кнопки

---

## 4. Utms и источники

Структура UTM:

```
?utm_source=<источник>&utm_medium=<тип>&utm_campaign=<кампания>&utm_content=<вариант>&utm_term=<ключ>
```

### Каналы
| Канал | utm_source | utm_medium | Пример |
|---|---|---|---|
| HH-outreach | hh | email | `?utm_source=hh&utm_medium=email&utm_campaign=apr26_sysadmin` |
| 1С-партнёр | 1c_francise | referral | `?utm_source=1c_francise&utm_medium=referral&utm_campaign=partner_xyz` |
| Habr | habr | blog | `?utm_source=habr&utm_medium=blog&utm_campaign=ransomware_article` |
| TG канал | tg | social | `?utm_source=tg&utm_medium=social&utm_campaign=launch` |
| Яндекс.Директ | yandex_direct | cpc | в Директе выставляется авто |
| Организика | (empty) | (empty) | — без параметров, из поиска |

---

## 5. Сегменты для анализа

В Метрике создать сегменты:

| Сегмент | Условие |
|---|---|
| «Горячие B2B» | source=направленный трафик + время ≥ 3 мин + scroll ≥ 75% |
| «Мобила» | device=mobile |
| «Из Habr» | utm_source=habr |
| «Готовые к покупке» | viewed /docs/sla.html OR /docs/offer.html |
| «Ушли с формы» | form_start = true AND form_submit = false |

---

## 6. Карта кликов и скроллов

- **Карта кликов** — раз в неделю смотрим, где кликают не там, где ждали.
- **Вебвизор** — раз в 2 недели смотрим 5 записей сессий «ушедших с формы».

---

## 7. Еженедельный dashboard (в Метрике)

1. Visits by source (utm_source).
2. CR по воронке (1→6 ступеней).
3. Top-10 страниц по просмотрам.
4. Формы: submits / errors / 429-retries.
5. Новые vs returning users.
6. Время на сайте (avg).

---

## 8. Алерты

Настроить Telegram-алерты (через Метрика API + наш alert.py или просто
вручную):

| Событие | Порог | Действие |
|---|---|---|
| 0 form_submit за сутки в рабочий день | 0 | Проверить, не упал ли backend |
| form_submit в 10× выше среднего за час | >10× | Возможен спам-атак, проверить логи |
| Новый trending keyword в поиске | ≥ 10 визитов за день | Писать статью под этот ключ |
| bounce rate > 80% на статье блога | — | Пересмотреть содержание |

---

*Обновлено: v4.4 · 2026-06 · актуальные типы целей 2025-2026, no-code опции*