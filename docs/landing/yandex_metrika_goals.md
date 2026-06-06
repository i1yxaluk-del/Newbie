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

### Цели (в порядке воронки)

| № | Название | Тип | Условие | Целевой CR |
|---|---|---|---|---:|
| 1 | visit_landing | Автоматически | — | 100% (baseline) |
| 2 | scroll_50 | JS-событие | `scroll >= 50%` | 60% |
| 3 | scroll_pricing | JS-событие | `scrolled into #pricing` | 35% |
| 4 | cta_click | JS-событие | клик по `.btn-primary` в любой секции | 12% |
| 5 | form_start | JS-событие | `change` любого input формы | 8% |
| 6 | form_submit | JS-событие | успешный POST /api/leads | **3%** (цель) |

### Как отправлять события (в React)

```js
// Пример: в Pricing.jsx при клике на тариф
window.ym && window.ym(COUNTER_ID, 'reachGoal', 'cta_click');
```

Установить COUNTER_ID в `.env.production` через `REACT_APP_YM_COUNTER_ID`.

---

## 3. Цели-вспомогательные

| Название | Условие | Зачем |
|---|---|---|
| doc_privacy_viewed | visit /docs/privacy.html | evaluation signal |
| doc_sla_viewed | visit /docs/sla.html | evaluation signal, hot |
| doc_offer_viewed | visit /docs/offer.html | evaluation signal, hot |
| calc_completed | пользователь заполнил калькулятор (если внедрим) | engagement + intent |
| time_on_page_180 | ≥ 3 мин на главной | high-engagement |
| form_field_error | toast.error из формы | UX-проблема |
| lead_form_429 | 429 Rate limit | spam-атака или легит-наплыв |

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

*Обновлено: v4.3 · 2026-06 · новый интерфейс Метрики (профиль сайта, 2025+) + SPA установка*