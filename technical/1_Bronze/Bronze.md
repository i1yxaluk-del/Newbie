# Bronze · Мастер-гайд

> **Цель документа:** за 30 минут чтения junior понимает, **что такое Bronze**, **из чего он
> состоит**, **с какой стороны подходить** к клиенту и **где найти детали**.
>
> **Обновлено:** v3.1 (апрель 2026).

## 1. Суть тарифа

Bronze — **базовый уровень защиты от катастрофы**. Минимум, чтобы клиент «не проснулся с
потерянным 1С / сайтом / файлами». 

| Параметр | Значение |
|---|---|
| Цена | от **25 000 ₽/мес** |
| Setup fee | 15 000 – 25 000 ₽ |
| SLA P1 reaction | ≤ 4 часа в рабочее время |
| Кому | 1–5 серверов, малый бизнес |
| Наш предел | до **5 таких клиентов на 1 junior** |

## 2. Что технически входит

### Мониторинг
- **Prometheus** — опрашивает все серверы клиента каждые 15 секунд
- **Grafana** — dashboard-ы CPU / RAM / диск / сеть / сервисы
- **Alertmanager** → Telegram-чат клиента и наш `#incidents`

### Бэкапы
- **restic** — инкрементальное шифрованное копирование в Yandex S3 (AES-256)
- Ежедневно в 3:00, утренняя автопроверка снапшота
- Retention: 7 daily + 4 weekly + 6 monthly

### Доступ
- **WireGuard Bastion** — единая точка входа, без открытых RDP/SSH наружу
- У клиента — только WG-конфиг, больше «внешнего периметра» нет

### Отчётность
- **Weekly report** — uptime, инциденты, тренды (PDF + Telegram)
- 1 час/мес консультаций по скайпу/Telegram

### Сервисы клиента, которые мы мониторим по Bronze
Для каждого — детальный playbook в [`../0_Common/SERVICES/`](../0_Common/SERVICES/):
- [`website.md`](../0_Common/SERVICES/website.md) — сайты и лендинги
- [`1c_server.md`](../0_Common/SERVICES/1c_server.md) — 1С (базовый уровень: хост + процессы rphost)
- [`file_server.md`](../0_Common/SERVICES/file_server.md) — файл-сервер (Samba/SMB)
- [`mail_dns.md`](../0_Common/SERVICES/mail_dns.md) — почта и DNS (внешний blackbox)
- [`database.md`](../0_Common/SERVICES/database.md) — БД (только хост-метрики; БД-специфика — Silver+)

Что в Bronze **НЕ входит**:
- ❌ Централизованные логи (Loki) — Silver
- ❌ Автоматизация Ansible/Puppet — Silver
- ❌ AD / FreeIPA управление — Silver (мониторинг — Bronze, управление — Silver)
- ❌ SIEM / EDR — Gold
- ❌ Тикет-система — Gold

## 3. Архитектура

```
                       ┌─────────────────────────────────┐
                       │    Yandex Cloud (наш)           │
                       │                                 │
                       │  ┌──────────────┐               │
Internet   ─UDP:51820─→│  │  Bastion VM  │  WG mesh     │
                       │  │  10.9.0.1    │              │
                       │  └───────┬──────┘              │
                       │          │                      │
                       │  ┌───────┴─────────────────┐    │
                       │  │   Monitoring VM         │    │
                       │  │   (2 vCPU / 4 GB)       │    │
                       │  │   Prometheus :9090      │    │
                       │  │   Grafana    :3000      │    │
                       │  │   Alertmanager :9093    │    │
                       │  │   restic client         │    │
                       │  └─────────────────────────┘    │
                       └─────────────────────────────────┘
                                   │ VPN (pull scrape)
              ┌────────────────────┼──────────────────┐
              │                    │                  │
       ┌──────┴──────┐     ┌───────┴──────┐    ┌──────┴──────┐
       │ Client 1    │     │  Client 2    │    │ Client N    │
       │ 10.9.0.10   │     │  10.9.0.11   │    │ 10.9.0.1X   │
       │ + agents    │     │  + agents    │    │ + agents    │
       │ + restic    │     │  + restic    │    │ + restic    │
       └─────────────┘     └──────────────┘    └─────────────┘
```

**Multi-tenancy:** один Monitoring VM обслуживает до 5 клиентов на Bronze.
При росте — см. [`../SCALING.md`](../SCALING.md).

## 4. Порядок развёртывания (полный цикл)

Для **исполнителя** (нас):
→ [`EXECUTOR/SOP_executor_bronze.md`](./EXECUTOR/SOP_executor_bronze.md)

Для **клиента**:
→ [`CLIENT/SOP_client_bronze.md`](./CLIENT/SOP_client_bronze.md)

Краткая последовательность (для быстрой памяти):
1. Bastion VM — см. `EXECUTOR/wireguard/setup_wireguard_bastion.sh`
2. Monitoring VM — docker-compose из `../0_Common/docker/`
3. Базовые alert rules — `EXECUTOR/prometheus/rules/bronze_alerts.yml`
4. Alertmanager маршруты — `../0_Common/alertmanager/alertmanager.yml`
5. **Для клиента:**
   - WireGuard клиент
   - Экспортёры (node / windows)
   - Restic backup
6. Добавить targets в `prometheus.yml` через `scripts/onboard_client.sh`
7. verify_all.sh bronze — всё зелёное

## 5. Бюджет инфраструктуры (Bronze)

| Ресурс | Цена/мес | Примечание |
|---|---|---|
| Bastion VM (1 vCPU / 2 GB) | 300 ₽ | shared между всеми Bronze-клиентами |
| Monitoring VM (2 vCPU / 4 GB / 30 GB SSD) | 700 ₽ | до 5 клиентов |
| Yandex S3 (до 100 GB backup/клиент) | 50 ₽/клиент | за объём архива |
| **Итого на нас** | **~1 000–1 400 ₽/клиент/мес** |

Маржа ≈ **92%** — см. [`../BUSINESS_MODEL.md`](../BUSINESS_MODEL.md).

## 6. Частые вопросы от клиента

> *Почему Bronze, а не просто мониторинг за 10k?*

Потому что в Bronze — не «просто мониторинг». Это комплекс: метрики + бэкапы + защищённый
доступ + договор + SLA. Любой из этих пунктов отдельно на рынке стоит 10–15k сам по себе.

> *Что если надо добавить +2 сервера сверх лимита?*

До 5 — входит в Bronze. 6–10 — остаёмся на Bronze, но ADDON `+сервер` 300 ₽/мес каждый.
Если серверов стабильно > 10 — правильнее Silver (там лимит 15 и включены логи).

> *Данные у нас?*

Ваши серверы — у вас. У нас только **метрики** (CPU, RAM, диск) и **зашифрованные бэкапы**
в Yandex S3. Ключ шифрования — у вас.

> *Что если вы закроетесь?*

В договоре прописано: при расторжении за 14 дней до — передаём git-конфиги, restic-пароль,
бэкапы. Вы можете продолжить обслуживать сами или передать другому подрядчику.

## 7. Приоритеты для владельца/senior

- [ ] Максимизировать количество **Bronze за счёт стандартизации**: чем более типовые клиенты —
      тем больше их обслуживает один junior.
- [ ] Сразу писать `client_configs/<slug>.yml` — через Ansible/Terraform повторяемость.
- [ ] Первые 3 Bronze-клиента = репутация. Ни одного простоя > SLA.

## 8. Upsell-возможности

Типичная траектория:
- Мес 1–3: Bronze, стабилизация
- Мес 4+: предложить Silver (если бизнес растёт и нужны логи / AD-управление)
- Мес 6+: ADDON-каталог — аудит, миграция 1С, внедрение MFA

См. [`../ADDONS.md`](../ADDONS.md).

## 9. Где искать дальше

- 🧑‍💻 **Junior начинает:** [`../Junior/ONBOARDING.md`](../Junior/ONBOARDING.md) → L1 задачи → экзамен L1
- 🛠 **Инженер:** `EXECUTOR/SOP_executor_bronze.md` + все скрипты в `EXECUTOR/`
- 📑 **Все runbook'и алертов Bronze:** [`../Junior/TROUBLESHOOTING.md`](../Junior/TROUBLESHOOTING.md)
- 💰 **Владельцу:** [`../BUSINESS_MODEL.md`](../BUSINESS_MODEL.md)
