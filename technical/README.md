# Technical Playbook — Навигатор по тарифам

> **Что здесь.** Техническая документация **по обслуживанию клиентов**:
> что входит в каждый тариф, какие SOP'ы выполняем, какие сервисы клиента
> поддерживаем, как происходит upsell и масштабирование.
>
> **Если ты хочешь развернуть наш сайт/инфру** (не клиента) — иди в
> [`../docs/deployment/README.md`](../docs/deployment/README.md).
>
> **Если ты Junior и проходишь обучение** — иди в
> [`../docs/training/README.md`](../docs/training/README.md).
>
> **Mail-стек:** outbound через Yandex Cloud Postbox на 587 (STARTTLS) —
> подробности в [`../deploy/yandex/STALWART_RELAY_MODE.md`](../deploy/yandex/STALWART_RELAY_MODE.md).

---

## Тарифы — мастер-гайды

Каждый тариф = inclusive bundle сервисов. Silver ⊃ Bronze, Gold ⊃ Silver.

| Тариф | Цена | Серверов | SLA P1 | Мастер-гайд | Чем отличается от предыдущего |
|---|---:|---|---|---|---|
| **Bronze** | от 25 000 ₽/мес | 1–5 | ≤ 4 ч (раб. время) | [`1_Bronze/Bronze.md`](./1_Bronze/Bronze.md) | базовый: Prometheus + Grafana + Alertmanager + restic + AmneziaWG-overlay + Telegram/MAX-алерты |
| **Silver** | от 50 000 ₽/мес | 6–15 (80–300 сотр.) | ≤ 2 ч | [`2_Silver/Silver.md`](./2_Silver/Silver.md) | + Loki (логи) + Puppet (desired state) + Ansible Control Node + AD/DNS/GPO |
| **Gold** | от 85 000 ₽/мес | 16–30 | ≤ 1 ч, 24/7 | [`3_Gold/Gold.md`](./3_Gold/Gold.md) | + Wazuh SIEM + FIM + Kaspersky EDR (через KSC) + osTicket |

Юнит-экономика по тарифам: [`BUSINESS_MODEL.md`](./BUSINESS_MODEL.md) — маржа, целевая загрузка, точки апгрейда.
Доп-услуги (upsell): [`ADDONS.md`](./ADDONS.md).
План роста к 50 клиентам: [`SCALING.md`](./SCALING.md).

---

## Структура каталога

```
technical/
├── README.md                  ← вы здесь (тарифы)
├── BUSINESS_MODEL.md          экономика тарифов, матрица услуг, upsell-точки
├── SCALING.md                 1 → 50 клиентов
├── ADDONS.md                  каталог разовых работ
│
├── 0_Common/                  ← компоненты, общие для всех тарифов
│   ├── SERVICES/              каталог сервисов клиента (1С, AD, сайт, почта)
│   ├── docker/                docker-compose стек (Prometheus + Alertmanager)
│   ├── amneziawg/             AmneziaWG bootstrap + tenant_add (UDP/443)
│   ├── monitoring/            prometheus.yml + rules + alertmanager.yml
│   ├── ansible/               inventory + roles (baseline, mongo, nginx, awg_hub, …)
│   └── scripts/               dr_drill.sh, monthly_report.py, rotate_junior_access.sh
│
├── 1_Bronze/                  тариф Bronze (1–5 серверов)
│   ├── Bronze.md              ← мастер-гайд (входная точка)
│   ├── CLIENT/                что ставится у клиента + AmneziaWG client setup
│   └── EXECUTOR/              что мы держим у себя (monitoring stack)
│
├── 2_Silver/                  Silver = Bronze + Loki + Puppet + AD/GPO
│   ├── Silver.md
│   ├── CLIENT/
│   └── EXECUTOR/
│
└── 3_Gold/                    Gold = Silver + Wazuh + Kaspersky + osTicket
    ├── Gold.md
    ├── SOP_gold_complete.md
    ├── CLIENT/
    └── EXECUTOR/
```

---

## Сервисы клиента (что мы обслуживаем)

Не путать с тарифами. Тариф = bundle. **Сервис клиента** = конкретная
система у клиента (1С, AD, сайт, файл-сервер). Один клиент имеет 5–7
сервисов; в зависимости от тарифа мы их по-разному обслуживаем.

Каталог сервисов: [`0_Common/SERVICES/README.md`](./0_Common/SERVICES/README.md) — для каждого свой 5-шаговый цикл (приём → подключение → настройка → контроль → troubleshoot).

---

## По задачам — quick-jump

| Задача | Куда идти |
|---|---|
| Понять, что входит в тариф клиента | [`BUSINESS_MODEL.md`](./BUSINESS_MODEL.md) → «Матрица услуг» |
| Принять нового клиента | [`../docs/onboarding/pre_onboarding_checklist.md`](../docs/onboarding/pre_onboarding_checklist.md) + [`../docs/onboarding/welcome_package.md`](../docs/onboarding/welcome_package.md) |
| Поднять Prometheus-стек у себя | [`1_Bronze/EXECUTOR/SOP_executor_bronze.md`](./1_Bronze/EXECUTOR/SOP_executor_bronze.md) |
| Добавить клиентский subnet в AmneziaWG | [`0_Common/amneziawg/tenant_add.sh`](./0_Common/amneziawg/tenant_add.sh) (UDP/443, обфускация против РКН-DPI) |
| Настроить 1С-мониторинг | [`0_Common/SERVICES/1c_server.md`](./0_Common/SERVICES/1c_server.md) |
| Добавить AD в мониторинг | [`0_Common/SERVICES/ad_domain.md`](./0_Common/SERVICES/ad_domain.md) |
| Добавить FreeIPA | [`0_Common/SERVICES/freeipa_domain.md`](./0_Common/SERVICES/freeipa_domain.md) |
| Развернуть Loki | [`2_Silver/EXECUTOR/SOP_executor_silver.md`](./2_Silver/EXECUTOR/SOP_executor_silver.md) |
| Запустить Wazuh SIEM | [`3_Gold/EXECUTOR/SOP_executor_gold.md`](./3_Gold/EXECUTOR/SOP_executor_gold.md) |
| Алерт пришёл — что делать | [`../docs/runbooks/README.md`](../docs/runbooks/README.md) (R-01..R-11) |
| Продать upsell | [`ADDONS.md`](./ADDONS.md) |
| Растём — что менять | [`SCALING.md`](./SCALING.md) |

---

## Соглашения

### Формат SOP
1. **Цель** — что достигаем.
2. **Предусловия** — что должно быть до начала.
3. **Шаги** — нумерованный список команд/действий.
4. **Проверки** — как убедиться, что сделано правильно.
5. **Откат (rollback)** — если что-то пошло не так.
6. **DoD** — конкретные критерии «готово».

### Формат runbook (для алертов)
1. Заголовок = точное имя алерта в Prometheus/Alertmanager.
2. Severity (P1/P2/P3/P4).
3. Диагностика (1–5 шагов).
4. Типичные причины + действия.
5. Эскалация (когда звать senior / клиента).

Полный каталог runbook'ов: [`../docs/runbooks/README.md`](../docs/runbooks/README.md).

### Окружения

| Окружение | Назначение | Доступ |
|---|---|---|
| `sandbox` | Обучение junior, тесты | All engineers (write) |
| `staging` | Тесты перед прод | Senior only (write) |
| `prod` | Реальные клиенты | Owner + Senior (write) |

Никогда не тестируем на `prod` изменения, которые не прошли `staging`.

---

## Junior-материалы

Junior-каталог (`technical/Junior/`) был удалён при v4.3-cleanup — соло-оператор
не нанимает джуна на старте. Когда появится первый наёмный инженер
(trigger: MRR ≥ 150k + 3 клиента, см. [`../docs/roadmap/etape_4_sprints.md`](../docs/roadmap/etape_4_sprints.md) спринт 11),
для него актуально:

- [`../docs/training/README.md`](../docs/training/README.md) — 12-недельная программа.
- [`../docs/runbooks/README.md`](../docs/runbooks/README.md) — R-01..R-11 (реактивные сценарии).
- [`../docs/checklists/`](../docs/checklists/) — weekly / monthly / quarterly чек-листы.
- [`../docs/deployment/troubleshooting.md`](../docs/deployment/troubleshooting.md) — типовые ошибки развёртывания.
- [`../docs/deployment/secrets_management.md`](../docs/deployment/secrets_management.md) — Vaultwarden.

---

*Последняя ревизия: 2026-05 (v4.5 — рестрyктура навигации; AmneziaWG UDP/443; Postbox 587 STARTTLS).*
