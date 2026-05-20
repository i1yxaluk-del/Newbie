# Technical Playbook — Навигатор

> Техническая документация MSP-сервиса. Используется владельцем, senior-инженерами,
> junior-стажёрами и клиентами (часть материалов — только внутренние).

> **v3.0 (май 2026)** — SOPs переведены на **PowerShell-first** для
> администратора с **Windows 10**. Серверная сторона (Yandex Cloud,
> Ubuntu 22.04, Docker, WireGuard, Stalwart, Prometheus и т.д.) не
> изменилась — Linux-команды выполняются с Win10-станции через
> OpenSSH client (`ssh root@srv 'bash …'` или `... | ssh ... bash -s`).
> Управление Windows-серверами клиента — через PowerShell Remoting
> (`Invoke-Command`) / WinRM / RDP. Подробнее: [`CHANGELOG.md`](../CHANGELOG.md).
>
> **Mail-стек Yandex Cloud:** Yandex Cloud блокирует TCP/25 на публичных
> IP VPC, поэтому Stalwart работает в submit-only режиме на портах
> **465 (SMTPS)** и **587 (STARTTLS)**, входящие письма принимаются через
> внешний MX-провайдер (Yandex 360 / Mailgun routes / Cloudflare Email
> Routing) с форвардом на `:587`. Подробности — в
> [`deploy/yandex/STALWART_RELAY_MODE.md`](../deploy/yandex/STALWART_RELAY_MODE.md).

## Структура документации

```
technical/
├── README.md                  ← этот файл (навигатор)
├── BUSINESS_MODEL.md          ← экономика тарифов, структура выручки
├── SCALING.md                 ← рост от 1 к 50 клиентам
├── ADDONS.md                  ← каталог доп.услуг (upsell/projects)
│
├── 0_Common/                  ← межтарифные компоненты
│   ├── SERVICES/              ← сервисы клиента (1С, AD, сайт и т.п.)
│   ├── docker/                ← общий docker-compose
│   ├── wireguard/             ← шаблоны WG
│   ├── alertmanager/          ← общий alertmanager.yml
│   └── scripts/               ← verify_all.sh и т.п.
│
├── 1_Bronze/                  ← тариф Bronze
│   ├── Bronze.md              ← мастер-гайд (входная точка)
│   ├── CLIENT/                ← всё, что ставится у клиента
│   └── EXECUTOR/              ← всё, что у нас (Monitoring VM)
│
├── 2_Silver/                  ← тариф Silver (= Bronze + автоматизация + AD/DNS/GPO + логи)
├── 3_Gold/                    ← тариф Gold (= Silver + SIEM + EDR + ticketing)
│
```

> **Junior-материалы.** Старый каталог `technical/Junior/` удалён при v4.3-cleanup:
> соло-оператор не нанимает джуна на старте. Когда появится первый наёмный инженер
> (trigger: MRR ≥ 150k + 3 клиента, см. `docs/roadmap/etape_4_sprints.md` спринт 11),
> для него актуальны:
> - [`docs/training/README.md`](../docs/training/README.md) — текущая программа обучения
> - [`docs/runbooks/`](../docs/runbooks/) — R-01..R-11 (реактивные сценарии)
> - [`docs/checklists/weekly.md`](../docs/checklists/weekly.md), [`monthly.md`](../docs/checklists/monthly.md), [`quarterly.md`](../docs/checklists/quarterly.md) — регулярные чек-листы
> - [`docs/deployment/troubleshooting.md`](../docs/deployment/troubleshooting.md) — типовые ошибки развёртывания
> - [`docs/deployment/secrets_management.md`](../docs/deployment/secrets_management.md) — Vaultwarden вместо старого `vault_guide`

---

## По ролям: где что искать

### 👑 Владелец / основатель
Приоритеты чтения:
1. [`BUSINESS_MODEL.md`](./BUSINESS_MODEL.md) — экономика
2. [`SCALING.md`](./SCALING.md) — план роста
3. [`ADDONS.md`](./ADDONS.md) — как повышать маржу
4. Мастер-гайды тарифов — общая картина того, что мы делаем

### 🧑‍💼 Sales / BDM
1. [`BUSINESS_MODEL.md`](./BUSINESS_MODEL.md) — тарифы и скоуп
2. [`ADDONS.md`](./ADDONS.md) — что предлагать после первой продажи
3. [`0_Common/SERVICES/`](./0_Common/SERVICES/) — чтобы понимать, «что клиенту можно и нельзя обещать»
4. [`../docs/onboarding/pre_onboarding_checklist.md`](../docs/onboarding/pre_onboarding_checklist.md) — «приём нового клиента»

### 👨‍💻 Senior инженер
1. Мастер-гайды тарифов (Bronze/Silver/Gold)
2. Все SOP для EXECUTOR
3. [`0_Common/SERVICES/`](./0_Common/SERVICES/) — экспертно
4. [`../docs/runbooks/`](../docs/runbooks/) — R-01..R-11 на каждый алерт
5. Ведёт и обновляет [`../docs/checklists/weekly.md`](../docs/checklists/weekly.md)

### 🎓 Junior (появится после MRR ≥ 150k · спринт 11 Этапа 4)
1. [`../docs/training/README.md`](../docs/training/README.md) — программа с нуля
2. [`0_Common/SERVICES/README.md`](./0_Common/SERVICES/README.md) — каталог сервисов
3. [`../docs/runbooks/`](../docs/runbooks/) — при инциденте
4. [`../docs/deployment/troubleshooting.md`](../docs/deployment/troubleshooting.md) — типовые ошибки
5. [`../docs/deployment/secrets_management.md`](../docs/deployment/secrets_management.md) — Vaultwarden

### 👤 Клиент (runbook-копии, которые можно делиться)
- `1_Bronze/CLIENT/SOP_client_bronze.md` (версия «что клиент сам делает»)
- SLA из приложения к договору
- Grafana ссылка (view-only)
- Emergency contact (Telegram)

---

## По задачам: quick-jump

| Задача | Куда идти |
|---|---|
| Понять, что входит в тариф клиента | [`BUSINESS_MODEL.md`](./BUSINESS_MODEL.md) → «Матрица услуг» |
| Принять нового клиента | [`../docs/onboarding/pre_onboarding_checklist.md`](../docs/onboarding/pre_onboarding_checklist.md) + [`../docs/onboarding/welcome_package.md`](../docs/onboarding/welcome_package.md) |
| Поднять Prometheus-стек у нас | [`1_Bronze/EXECUTOR/SOP_executor_bronze.md`](./1_Bronze/EXECUTOR/SOP_executor_bronze.md) |
| Настроить 1С-мониторинг | [`0_Common/SERVICES/1c_server.md`](./0_Common/SERVICES/1c_server.md) |
| Добавить AD в мониторинг | [`0_Common/SERVICES/ad_domain.md`](./0_Common/SERVICES/ad_domain.md) |
| Добавить FreeIPA | [`0_Common/SERVICES/freeipa_domain.md`](./0_Common/SERVICES/freeipa_domain.md) |
| Развернуть Loki | [`2_Silver/EXECUTOR/SOP_executor_silver.md`](./2_Silver/EXECUTOR/SOP_executor_silver.md) |
| Запустить Wazuh SIEM | [`3_Gold/EXECUTOR/SOP_executor_gold.md`](./3_Gold/EXECUTOR/SOP_executor_gold.md) |
| Алерт пришёл — что делать | [`../docs/runbooks/`](../docs/runbooks/) (R-01..R-11) |
| Продать upsell | [`ADDONS.md`](./ADDONS.md) |
| Растём — что менять | [`SCALING.md`](./SCALING.md) |

---

## Соглашения в документации

### Формат SOP
Все SOP следуют структуре:
1. **Цель** — что достигаем
2. **Предусловия** — что должно быть до начала
3. **Шаги** — нумерованный список команд/действий
4. **Проверки** — как убедиться, что сделано правильно
5. **Откат (rollback)** — если что-то пошло не так
6. **DoD (Definition of Done)** — конкретные критерии «готово»

### Runbook для алертов
1. Заголовок = точное имя алерта в Prometheus/Alertmanager
2. Severity (critical / warning / info)
3. Шаги диагностики (1–5)
4. Типичные причины
5. Действия для каждой причины
6. Эскалация (когда звать senior / клиента)

### Комментарии в коде
- **shell-скрипты:** комментарий к каждому значимому блоку, `set -euo pipefail` обязательно
- **yaml конфиги:** блок-комментарий перед каждой секцией, объясняющий назначение
- **puppet:** inline-комментарии на классах и значимых параметрах

### Версионирование документации
- Мелкие правки (опечатки, команды) — прямой push в main
- Изменения в логике (новые runbook'и, изменение алертов) — через PR с ревью senior
- Мастер-гайды тарифов — обновляются раз в квартал, с указанием даты ревизии

---

## Окружения

| Окружение | Назначение | Доступ |
|---|---|---|
| `sandbox` | Обучение junior, тесты | All engineers (write) |
| `staging` | Тесты перед продом | Senior only (write) |
| `prod` | Реальные клиенты | Owner + Senior (write) |

Никогда не тестируем на `prod` изменения, которые не прошли `staging`.

---

## Обновления

- **Последняя ревизия:** май 2026 (v3.0 — PowerShell-first SOPs + Stalwart submit-only 465/587)
- **Ответственный за documentation:** senior инженер (rotating quarterly)
- **Changelog:** в Notion, раздел «Documentation changes»

---

**Начни здесь** если ты новый junior:
→ [`../docs/training/README.md`](../docs/training/README.md)
