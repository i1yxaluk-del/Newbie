# Junior Onboarding: Первые 14 дней

> **Для кого:** новый инженер MSPShield без глубокого опыта MSP.
> **Результат к концу 14 дней:** junior может самостоятельно принимать клиента Bronze
> под надзором senior и вести дежурство L1.

## Обзор пути

```
Неделя 1 — ТЕОРИЯ + СТЕНД       (L0 — нулевой уровень)
Неделя 2 — ДУБЛЁР + ПРАКТИКА    (L1 — Bronze-готовность)
Далее    — ОБУЧЕНИЕ НА L2/L3     (см. junior_training.md)
```

---

## День 1 — Орг и аккаунты (4 часа)

- [ ] NDA + договор подписан
- [ ] Выданы доступы:
  - [ ] Jitsi / Telegram-чат команды
  - [ ] Bitwarden (Vault) — только свои учётки и shared Bronze
  - [ ] Git (read-only на production, read/write на `sandbox`)
  - [ ] Grafana — view-only на all dashboards
  - [ ] Prometheus — read-only (через reverse-proxy)
  - [ ] Yandex Cloud — IAM `viewer` на sandbox-фолдер
- [ ] Прочитать и расписаться:
  - [ ] [`../../technical/Junior/junior_training.md`](../junior_training.md) — программа в целом
  - [ ] [`/app/docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md) — ответственность за ПДн
  - [ ] [`../../technical/Junior/vault_guide.md`](../vault_guide.md) — работа с Bitwarden
- [ ] Выдать ноутбук (или подписать BYOD-регламент)
- [ ] Поставить на компьютер: SSH-клиент, WireGuard, Docker, git, vscode, `k9s` (для docker-compose)

**DoD дня 1:** junior зашёл по WireGuard в sandbox и увидел Grafana.

---

## День 2 — Теория архитектуры (6 часов)

- [ ] Прочитать мастер-гайды:
  - [ ] [`../1_Bronze/Bronze.md`](../../1_Bronze/Bronze.md)
  - [ ] [`../2_Silver/Silver.md`](../../2_Silver/Silver.md)
  - [ ] [`../3_Gold/Gold.md`](../../3_Gold/Gold.md)
- [ ] Нарисовать на бумаге схему сети клиента Bronze (проверка senior)
- [ ] Объяснить в чате команды своими словами:
  - Что делает Prometheus
  - Что делает Alertmanager
  - Что такое Bastion и зачем
  - Чем отличается node_exporter от windows_exporter
  - Зачем нужен restic (а не просто rsync)

**DoD:** senior ставит ✓ в HR-чек-листе.

---

## День 3 — Развёртывание Bronze-стека в sandbox (8 часов)

Junior **сам** разворачивает с нуля в песочнице:

- [ ] Поднять Yandex Cloud VM (2 vCPU / 4 GB / 30 GB)
- [ ] Следуя `1_Bronze/EXECUTOR/SOP_executor_bronze.md`:
  - [ ] Настроить WireGuard Bastion
  - [ ] Запустить Docker Compose stack (Prometheus + Grafana + Alertmanager)
  - [ ] Подключить node_exporter на тестовой Ubuntu-VM
  - [ ] Увидеть зелёные метрики в Grafana
- [ ] Сымитировать сбой: остановить node_exporter, увидеть алерт в тестовом Telegram-чате

**DoD:** senior удостоверяется, что stack поднят и алерт реально пришёл.

---

## День 4 — Клиентская сторона (8 часов)

- [ ] Прочитать [`../0_Common/SERVICES/README.md`](../../0_Common/SERVICES/README.md)
- [ ] По каждому сервису прогнать **теорию** (опросник + красные флаги):
  - [ ] website.md
  - [ ] 1c_server.md (даже если не будете сразу — надо понимать)
  - [ ] ad_domain.md
  - [ ] freeipa_domain.md
  - [ ] mail_dns.md
  - [ ] file_server.md
  - [ ] database.md
- [ ] Практика: настроить blackbox_exporter для 3 сайтов (любых публичных) и получить `probe_success == 1` в grafana
- [ ] Практика: сделать restic backup папки `/tmp/test-data` → S3 sandbox и обратно restore в `/tmp/restored`

**DoD:** файл `restored/` bit-identical исходному.

---

## День 5 — Трёхчасовой mock-аудит (4 часа)

Senior играет «клиента» — юр.фирма 30 чел., 2 сервера:
- Почта на Яндекс 360
- 1С:Предприятие (клиент-серверный, PostgresPro)
- Файловый сервер Samba
- Сайт на Timeweb

Junior должен за 30 минут:
- Заполнить опросники по каждому сервису
- Найти 5 красных флагов (senior закладывает их осознанно)
- Предложить корректный тариф (Bronze / Silver / Gold)
- Набросать план онбординга: что в день 1/2/3
- Предложить 1–2 upsell

**DoD:** senior ставит 4+ из 5 (тариф, флаги, план, upsell, качество вопросов).

---

## День 6-7 — Выходные на чтение

- [ ] Пройти курс «Prometheus for beginners» (youtube, ~4 часа)
- [ ] Прочитать про PromQL (операторы, labels, rate vs irate)
- [ ] Написать 5 собственных PromQL-запросов для тестовых метрик в sandbox

---

## Неделя 2: Дублёр на реальных клиентах

Junior в режиме **shadow** присутствует с senior при всех операциях у клиента:

- [ ] День 8: Еженедельная проверка 2 клиентов Bronze (делает senior, junior наблюдает)
- [ ] День 9: Junior сам делает weekly-check одного Bronze, senior проверяет
- [ ] День 10: Онбординг нового клиента под руководством senior
  - Junior выполняет все шаги install-скриптов
  - Senior подписывает каждый шаг
- [ ] День 11: Alert в 2:00 ночи → senior поднимает, junior подключается (opt-in)
- [ ] День 12: Первое самостоятельное дежурство L1 (рабочее время, senior на связи)
- [ ] День 13: Обработка 3 алертов разного уровня (WARN/CRIT), описание пост-мортем
- [ ] День 14: Ревью с senior. Решение о допуске к L1-сертификации.

---

## Критерии допуска к L1 (Bronze)

После 14 дней junior может самостоятельно выполнять:

- ✅ Еженедельные проверки Bronze-клиента (weekly_report.sh + визуальная сверка)
- ✅ Онбординг нового Bronze-клиента (под запись в Notion, с ревью senior в конце дня)
- ✅ Реакция на WARN-алерт в рабочее время (по runbook)
- ✅ Реакция на CRIT-алерт с эскалацией (15 мин — связаться с senior)
- ✅ Написать короткий пост-мортем после инцидента

Чего junior **пока не делает** без senior:
- ❌ Менять прод-конфиги (prometheus.yml, alert rules) — только PR в git
- ❌ Восстанавливать AD из System State
- ❌ Восстанавливать FreeIPA из ipa-backup (CA-сертификаты — это подрыв компании)
- ❌ Любые работы с Kaspersky Security Center
- ❌ Общаться один-на-один с директором клиента по стратегии (только тех. вопросы)
- ❌ Оформлять upsell на > 50k₽ без согласования senior

## Далее — L2 (Silver) и L3 (Gold)

См. [`junior_training.md`](./junior_training.md) — программа на месяцы 2–6.
