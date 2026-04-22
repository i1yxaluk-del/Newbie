# Цели Яндекс.Метрики — настройка

> Все цели должны быть настроены в Метрике **до первой платной
> рекламной кампании**. Иначе у нас нет data для оптимизации.

---

## 1. Композитная воронка «визит → лид»

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

## 2. Цели-вспомогательные

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

## 3. Utms и источники

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

## 4. Сегменты для анализа

В Метрике создать сегменты:

| Сегмент | Условие |
|---|---|
| «Горячие B2B» | source=направленный трафик + время ≥ 3 мин + scroll ≥ 75% |
| «Мобила» | device=mobile |
| «Из Habr» | utm_source=habr |
| «Готовые к покупке» | viewed /docs/sla.html OR /docs/offer.html |
| «Ушли с формы» | form_start = true AND form_submit = false |

---

## 5. Карта кликов и скроллов

- **Карта кликов** — раз в неделю смотрим, где кликают не там, где ждали.
- **Вебвизор** — раз в 2 недели смотрим 5 записей сессий «ушедших с формы».

---

## 6. Еженедельный dashboard (в Метрике)

1. Visits by source (utm_source).
2. CR по воронке (1→6 ступеней).
3. Top-10 страниц по просмотрам.
4. Формы: submits / errors / 429-retries.
5. Новые vs returning users.
6. Время на сайте (avg).

---

## 7. Алерты

Настроить Telegram-алерты (через Метрика API + наш alert.py или просто
вручную):

| Событие | Порог | Действие |
|---|---|---|
| 0 form_submit за сутки в рабочий день | 0 | Проверить, не упал ли backend |
| form_submit в 10× выше среднего за час | >10× | Возможен спам-атак, проверить логи |
| Новый trending keyword в поиске | ≥ 10 визитов за день | Писать статью под этот ключ |
| bounce rate > 80% на статье блога | — | Пересмотреть содержание |

---

*Обновлено: v4.1 · 2026-04*
