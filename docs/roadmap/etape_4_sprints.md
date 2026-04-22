# Этап 4 · 12 спринтов × 2 недели = 24 недели

Этот план — **как именно** превратить артефакты v4.1 в первого
платящего клиента и плавный рост до 3-5 клиентов к концу 24 недели, в
рамках [стратегических решений](strategic_decisions.md) и
[бюджетных ограничений](budget_constraints.md).

## Правила спринта

- **Длина:** 2 недели, с пятницы до четверга.
- **Бюджет времени:** 10-12 ч муж + 5-8 ч супруга. Не больше. Если спринт просит больше — cut scope.
- **Обязательный артефакт спринта:** 1 commit в репозитории (если применимо) + 1 запись в retrospective Kaiten.
- **DoD (Definition of Done) каждого спринта:** сверху артефакты/контрольные точки.
- **Retro:** в конце каждого спринта, 60 мин, с супругой. Ответить 3 вопроса: что получилось / что не успел / что cut'ать в следующий.

## Сводка

| # | Фокус | Клиент-цель | Artifact-цель |
|---:|---|---|---|
| 1 | Security P0 + инфра dev | — | v4.1 мёрж, tf dev-stack, landing draft |
| 2 | Landing go-live + метрика | 10+ визитов/день | SEO, JSON-LD, Метрика, A/B #1 |
| 3 | HH-hunter kick-off | 5 подходящих вакансий | HH playbook, 10 outreach |
| 4 | 1С-франчайзи + cold | 2 warm-lead | 1С-outreach, cold-call script |
| 5 | Первый discovery-звонок | 1 BANT-Q-лид | BANT-Q скрипт применён, weekly ритм |
| 6 | Первый Bronze-клиент онбординг | 1 закрытая сделка | Bronze onboarding по Day 1-7 |
| 7 | Стабилизация · первые runbook'и в деле | 1 активный клиент, 0 P1 | Retro R-XX, monthly-report |
| 8 | Второй Bronze | 2 активных | Repeat sales playbook, A/B #2 |
| 9 | Silver-лид · квалификация | 3 активных / 1 Silver-proposal | BANT-Q для Silver, AD-readiness |
| 10 | Первый Silver онбординг | 3 активных + 1 Silver-onboarding | Silver SOP в деле, AD-checks |
| 11 | Break-even check + найм Junior (если MRR ≥ 150k) | MRR check | Junior JD live, screening |
| 12 | Junior onboarding · DR drill · retro 24-недельный | 3-5 активных · Junior онбординг week 1 | DR drill пройден · Etape-5 ретро |

## Детали спринтов

---

### Спринт 1 · Security P0 + dev-инфра (W1-W2)

**Цель.** Не падает: backend проверяет consent/rate-limit/honeypot. Landing — запускается локально. Terraform dev-stack развёрнут.

**Муж (12 ч).**
- [ ] Merge PR #2 в main, tag v4.1.
- [ ] `cd deploy && docker compose up -d` — локально поднять стек, убедиться `curl /api/health` отвечает.
- [ ] `cd infra/terraform && terraform init && terraform plan` — смотрим, что план адекватен. **НЕ apply** пока.
- [ ] Заказать домен `mspshield.ru` (или доступный аналог). ≤ 1 000 ₽/год.
- [ ] Настроить Яндекс.Почта для домена (free).
- [ ] Подписать внутрисемейный NDA с супругой (распечатать / эл. подписать).

**Супруга (5 ч).**
- [ ] Изучить `docs/onboarding/welcome_package.md` и `docs/sales/email_templates.md`.
- [ ] Создать Kaiten workspace. Завести pipeline по [funnel_6_stages](../sales/funnel_6_stages.md).
- [ ] Регистрация в «Мой налог» (если ещё не). Завести test-чек на 100 ₽.

**DoD.**
- PR #2 мёрж, тег `v4.1` на `main`.
- Локальный стек (docker compose) стартует с одной команды.
- Домен куплен, DNS привязан.
- Kaiten workspace готов.

---

### Спринт 2 · Landing go-live + Яндекс.Метрика (W3-W4)

**Цель.** Первый публичный лендинг. Метрика собирает данные. Запущен A/B-эксперимент #1 (H1 hero-copy).

**Муж (10 ч).**
- [ ] `terraform apply` — поднимается landing + bastion VM в Yandex Cloud.
- [ ] Ansible: `ansible-playbook playbooks/site.yml` на landing-хосте.
- [ ] Certbot → SSL от Let's Encrypt.
- [ ] DNS cutover: mspshield.ru → landing IP.
- [ ] Smoke-test: форма отправляет лид → telegram-уведомление.
- [ ] CSP и security headers (см. `deploy/nginx/mspshield.conf`) проверить.

**Супруга (7 ч).**
- [ ] Яндекс.Метрика: создать счётчик, вставить код в index.html.
- [ ] Настроить 6 целей из [`yandex_metrika_goals.md`](../landing/yandex_metrika_goals.md).
- [ ] A/B-эксперимент #1: две версии H1 заголовка (из [ab_testing.md](../landing/ab_testing.md)). 50/50.
- [ ] Первое тестовое письмо "test lead" — проверить, что воронка Kaiten сработала.

**DoD.**
- Landing публичен: `https://mspshield.ru` открывается.
- Форма отправляет лид → backend → Telegram.
- Метрика фиксирует визиты и цели.
- A/B-эксперимент #1 запущен.

---

### Спринт 3 · HH-hunter kick-off (W5-W6)

**Цель.** Первые 10 HH-outreach писем отправлены.

**Муж (10 ч).**
- [ ] Написать [`docs/sales/hh_hunter_playbook.md`](../sales/hh_hunter_playbook.md) — workflow:
  1. Поиск вакансий по фильтрам («сисадмин», «системный администратор», «IT-специалист» + город + компания 20-100 чел).
  2. Quick-score: есть ли явный признак боли? (дробный график, 24/7, «без опыта»).
  3. Адаптация email из [`email_templates.md`](../sales/email_templates.md#template-2-hh-outreach).
- [ ] Список 30 потенциальных компаний.
- [ ] Отправить 10 первых писем из списка.

**Супруга (8 ч).**
- [ ] Отследить open-rate / reply-rate. Записать в Kaiten.
- [ ] Follow-up (D+3) тем, кто не ответил.
- [ ] Первая ретро-заметка по каналу (какие сегменты отвечают лучше).
- [ ] Регистрация профиля на FL.ru и Хабр Фриланс — nice-to-have.

**DoD.**
- HH-hunter playbook написан и закоммичен.
- 10 outreach-писем отправлены.
- Open-rate/reply-rate измерен.

---

### Спринт 4 · 1С-франчайзи + cold-call (W7-W8)

**Цель.** 2 warm-lead (это могут быть «приятные ответы», не подписанные сделки).

**Муж (10 ч).**
- [ ] Написать [`docs/sales/1c_partner_outreach.md`](../sales/1c_partner_outreach.md): 15-минутное предложение «мы делаем 24/7 мониторинг серверов 1С, можно направлять ваших клиентов».
- [ ] Список 20 1С-франчайзи в регионе. Отправить 10 outreach.
- [ ] Написать [`docs/sales/cold_call_script.md`](../sales/cold_call_script.md) — 4-минутный разговор по телефону.
- [ ] Провести 5 cold-call'ов по списку компаний с "красным флагом" (недавно уволили сисадмина по LinkedIn/HH).

**Супруга (6 ч).**
- [ ] Написать [`docs/sales/tg_community_presence.md`](../sales/tg_community_presence.md): правила presence в сис-админских, 1С, импортозамещение TG-чатах.
- [ ] Вступить в 5 TG-чатов. Первая неделя — только слушаем. Вторая неделя — отвечаем на 2-3 вопроса без продажи.
- [ ] Follow-up по выдохнувшим HH-лидам из спринта 3.

**DoD.**
- 3 новых sales doc'а ([1c_partner_outreach](../sales/1c_partner_outreach.md), [cold_call_script](../sales/cold_call_script.md), [tg_community_presence](../sales/tg_community_presence.md)).
- 10 outreach 1С + 5 cold-call.
- 2 warm-lead в Kaiten.

---

### Спринт 5 · Первый discovery-звонок (W9-W10)

**Цель.** 1 BANT-qualified лид с подписанным NDA. Weekly ритм с супругой отработан.

**Муж (10 ч).**
- [ ] Провести 2 discovery-звонка с warm-лидами из спринта 4 (по [bant_q_script](../sales/bant_q_script.md)).
- [ ] Подготовить коммерческое предложение (ценностное, не прайсовое) — по итогам 1 лучшего звонка.
- [ ] Если есть готовность — подписание NDA и передача [pre_onboarding_checklist](../onboarding/pre_onboarding_checklist.md).

**Супруга (6 ч).**
- [ ] Присутствовать на discovery-звонках как note-taker.
- [ ] Отработать ритм: пн. 15 мин планёрка + пт. 30 мин ретро.
- [ ] A/B-эксперимент #2: CTA-кнопка «Получить аудит» vs «Записаться на звонок».

**DoD.**
- 1+ BANT-qualified лид в стадии "proposal sent".
- Weekly-ритм с супругой работает 2 недели подряд.
- A/B #2 запущен.

---

### Спринт 6 · Первый Bronze-клиент онбординг (W11-W12)

**Цель.** Bronze-клиент подписан + прошёл Day 1-7 онбординг.

**Муж (12 ч).**
- [ ] Подписание контракта (НПД, из [`contracts/contract_bronze.html`](../../contracts/contract_bronze.html) с правками под НПД).
- [ ] Провести [`day_1_7_runbook`](../onboarding/day_1_7_runbook.md).
- [ ] Terraform: добавить tenant — новая WireGuard подсеть, [tenant_add.sh](../../technical/0_Common/wireguard/tenant_add.sh).
- [ ] Ansible: развернуть Bronze stack у клиента (monitoring + restic + hardening).
- [ ] Первый backup восстановлен (smoke test) — доказательство клиенту.

**Супруга (8 ч).**
- [ ] [Welcome package](../onboarding/welcome_package.md) отправлен.
- [ ] Первый weekly-sync проведён с клиентом (она — host, муж — on standby).
- [ ] Запись о первом Kaiten-client-card заведена.

**DoD.**
- Bronze-клиент на prod, мониторинг работает, первый backup есть.
- Welcome package отправлен, weekly-sync пройден.
- Супруга имеет доступ к client-card в Kaiten (без prod доступа).

---

### Спринт 7 · Стабилизация · первые runbook'и в деле (W13-W14)

**Цель.** 1 активный клиент, 0 P1-инцидентов, monthly-report отправлен.

**Муж (10 ч).**
- [ ] Ответить на все non-critical alerts / P3 тикеты по runbook'ам.
- [ ] Провести первый [monthly_report.py](../../technical/0_Common/scripts/monthly_report.py) — полный pipeline от метрик до markdown.
- [ ] Первый DR smoke-drill по [R-11](../runbooks/R-11.md) — короткий, 30 минут.

**Супруга (6 ч).**
- [ ] Собрать feedback от клиента (что хорошо / плохо в первый месяц).
- [ ] Обновить страницы `cases.jsx` (если клиент согласен на упоминание, даже без имени).
- [ ] A/B #3 запуск.

**DoD.**
- Monthly-report отправлен клиенту.
- Первый DR-drill пройден (smoke).
- Клиент дал первый NPS/feedback.

---

### Спринт 8 · Второй Bronze + repeat sales (W15-W16)

**Цель.** 2 активных клиента, sales-воронка repeatable.

**Муж (10 ч).**
- [ ] Onboarding второго Bronze.
- [ ] Patch-window плановая по [R-10](../runbooks/R-10.md) на первом клиенте.
- [ ] Первые outreach с «case-study» (анонимный первый клиент).

**Супруга (8 ч).**
- [ ] Обновить email-templates с real-world фрагментами.
- [ ] A/B #4 запуск.
- [ ] Начать отдельный pipeline для «пассивных лидов, дозревающих» — follow-up 1 раз/месяц.

**DoD.**
- 2 активных клиента.
- Voronka повторяется: outreach → discovery → proposal → close за < 8 недель.

---

### Спринт 9 · Silver-лид · квалификация (W17-W18)

**Цель.** 3 активных клиента (может 2 Bronze + 1 Silver-proposal). Readiness для AD/GPO-клиентов.

**Муж (12 ч).**
- [ ] Проверить, что Silver-playbook актуален (`technical/2_Silver/`).
- [ ] Запустить Windows-lab для тренировок AD в test-env (из [week_07.md](../training/week_07.md)).
- [ ] Технический discovery Silver-лида.

**Супруга (8 ч).**
- [ ] Разослать case-study по HH/1С backlog'у.
- [ ] Обзвон существующих клиентов — upsell на Silver / ADDON?
- [ ] A/B #5.

**DoD.**
- 1 Silver-лид в стадии "proposal sent".
- Windows-lab для AD-тренировок готов.

---

### Спринт 10 · Первый Silver онбординг (W19-W20)

**Цель.** 3 активных (2 Bronze + 1 Silver). Silver-онбординг выполнен.

**Муж (12 ч).**
- [ ] Подписание Silver-контракта (НПД, из [`contract_silver.html`](../../contracts/contract_silver.html)).
- [ ] Ansible role `loki` + `puppet` проверен на test-lab.
- [ ] Silver onboarding по [day_1_7_runbook](../onboarding/day_1_7_runbook.md) + AD-checks.

**Супруга (8 ч).**
- [ ] Silver welcome-package — более детальный (SLA, on-call window).
- [ ] Первый Silver weekly-sync.

**DoD.**
- Silver-клиент на prod.
- AD-checks идут в Prometheus (ad_replication_lag alert живой).

---

### Спринт 11 · Break-even check + начало найма Junior (W21-W22)

**Цель.** Решение: MRR ≥ 150k? 3+ активных клиента? 2 мес без P1? → запускаем найм.

**Муж (10 ч).**
- [ ] Пересчитать [`finmodel_m1_m24.md`](../../analysis/finmodel_m1_m24.md) с реальными данными.
- [ ] Опубликовать [junior_jd](../hiring/junior_jd.md) (на HH, в TG-каналы, сарафан).
- [ ] Провести 2-3 [screening-звонка](../hiring/screening_call.md).

**Супруга (8 ч).**
- [ ] Подготовить очередь тест-заданий ([test_task.md](../hiring/test_task.md)).
- [ ] Опрос клиентов по NPS (через 3-5 мес после старта).

**DoD.**
- Финансовая модель обновлена с реальными данными.
- Junior JD опубликована (если go-trigger достигнут).
- 2-3 screening-звонка проведены.

**Если go-trigger НЕ достигнут:**
- Переформатировать этот спринт в «стабилизация», сохранение текущей клиентской базы без новых наборов.
- Отложить Junior на M7.

---

### Спринт 12 · Junior onboarding · DR drill · retro 24-недель (W23-W24)

**Цель.** Junior week 1-2 ([week_01.md](../training/week_01.md)) + квартальный DR drill + retrospective на весь Этап 4.

**Муж (10 ч).**
- [ ] Junior week 1 pairing (подписание NDA → доступы → первые P3 в паре).
- [ ] Квартальный DR drill (полный, не smoke) по [R-11](../runbooks/R-11.md).
- [ ] Retrospective: что получилось, что не получилось, что на следующие 24 недели?

**Супруга (6 ч).**
- [ ] Quarterly-отчёт каждому клиенту.
- [ ] Собрать Junior onboarding feedback.

**DoD.**
- Junior неделя 1 пройдена.
- Квартальный DR drill пройден.
- Retrospective-документ написан в `docs/roadmap/etape_4_retro.md` (появится на месяц 6).

---

## После 24 недель

**Если go-trigger достигнут:**
- Переход к Этапу 5: расширенная операционная модель, 2 Junior'а, попытка Gold-клиента.
- План v4.3/v5.0.

**Если не достигнут:**
- Или останавливаемся (burnout) — и сохраняем артефакты как open-source.
- Или пересматриваем каналы (третий канал, платная реклама если есть ресурсы).
- Или переформатируем в side-project mode (1-2 клиента долгосрочно, минимум усилий).

---

## Ключевые метрики (еженедельно)

| Метрика | Источник | Таргет к W24 |
|---|---|---:|
| Посетителей лендинга / нед | Яндекс.Метрика | 100+ |
| Заявок через форму / нед | backend `/metrics` | 2-3 |
| BANT-qualified / нед | Kaiten | 1-2 |
| Активных клиентов | Kaiten + биллинг | 3-5 |
| MRR | Excel | 150 000 ₽ |
| P1 инциденты / мес | Kaiten | 0-1 |
| Часов мужа / нед | Toggl | ≤ 15 |
| Burnout-score мужа (1-10) | self-report | ≤ 5 |
| NPS клиентов | опрос | ≥ 8 |

## Cut first (если мало времени)

Порядок, в котором спринты можно **cut'ать/отложить**:
1. A/B-эксперименты #3+ (#1-#2 обязательны).
2. TG-community presence.
3. Блог (уже deferred).
4. Silver-клиент (если Bronze-поток хорош).
5. Junior (если MRR < 150k).

Порядок, который **никогда не cut'ается**:
1. Security P0 (спринт 1).
2. Landing публикация (спринт 2).
3. Первый BANT-звонок (спринт 5).
4. Первый клиент onboarding (спринт 6).
5. Monthly-report первому клиенту (спринт 7).
6. DR-drill квартальный (спринт 12 / каждый квартал).
