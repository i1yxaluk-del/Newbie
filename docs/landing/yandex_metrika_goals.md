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