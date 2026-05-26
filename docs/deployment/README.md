# Развёртывание MSPShield — оглавление

> **Канонический deploy-flow.** Инструкции по развёртыванию всего стека
> MSPShield на русском, от локальной разработки до первого клиента в
> продакшене. Если попал сюда из корневого README — ты на правильной
> странице.

## Два пути к проду

В репо живут **два независимых пути** к продакшен-лендингу. Выбери один:

| Путь | Когда выбрать | Подробности |
|---|---|---|
| **Path A** — единая VM, Caddy + Docker, `deploy.ps1` | Быстро поднять MVP с Windows-машины (PowerShell-флоу). Сайт + bastion на одном статическом IP. **TCP/443 у Caddy + UDP/443 у AmneziaWG — не конфликтуют.** | [`../../deploy/yandex/README.md`](../../deploy/yandex/README.md) |
| **Path B** — две VM (landing + bastion), Terraform + Ansible + Nginx | Production-grade с разделением ролей, IaC, повторяемостью. | [`landing_production.md`](landing_production.md) |

Дальше документ описывает оба пути одинаково через сценарии A/B/C.

## Три сценария (выбирай по цели)

| # | Сценарий | Когда нужен | Время | Куда смотреть |
|---|----------|-------------|-------|---------------|
| 1 | **Локальная разработка** | Редактируешь код, хочешь увидеть лендинг на `localhost` | ~20 мин | [`local_dev.md`](local_dev.md) |
| 2 | **Продакшен-лендинг** | Первый запуск бизнеса: домен, VM в Yandex Cloud, SSL, публичный сайт | 4–6 ч | [`landing_production.md`](landing_production.md) |
| 3 | **Онбординг клиента (тенант)** | Подписан контракт с клиентом — надо развернуть Bronze/Silver стек | 4–8 ч на Bronze, 1–2 дня на Silver | [`tenant_onboarding.md`](tenant_onboarding.md) |

Дополнительно:

- [`secrets_management.md`](secrets_management.md) — где хранить пароли, токены, SSH-ключи (Vaultwarden + Yandex Lockbox).
- [`disaster_recovery.md`](disaster_recovery.md) — что делать, если всё упало.
- [`troubleshooting.md`](troubleshooting.md) — типовые ошибки и как их чинить.

---

## Архитектура в одной картинке

```
                          ┌──────────────────────┐
                          │      Интернет        │
                          │ (клиенты, браузеры)  │
                          └──────────┬───────────┘
                                     │ HTTPS 443
                                     ▼
          ┌───────────────────────────────────────────────┐
          │   mspshield-landing (Yandex Cloud VM)         │
          │                                               │
          │   nginx 80/443 (TLS) ──► React static         │
          │                   └────► FastAPI 8001         │
          │                              │                │
          │                              ▼                │
          │                       MongoDB 27017 (local)   │
          └───────────────────────────────────────────────┘
                     ▲
                      │ AmneziaWG 10.9.0.0/24 (UDP/443)
                     │
          ┌──────────┴──────────────────────────┐
          │   mspshield-bastion (Yandex Cloud)  │
          │                                     │
          │   awg0 UDP 443  ◄───┐               │
          │                     │               │
          │   Vaultwarden       │               │
          │   Prometheus/Alertmanager           │
          └─────────────────────┼───────────────┘
                                │ AmneziaWG 10.20.x.x
                                ▼
          ┌──────────────────────────────────────┐
          │   Tenant VMs (каждый клиент — /24)   │
          │   10.20.10.0/24 — acme               │
          │   10.20.11.0/24 — beta-co            │
          │   ...                                │
          │   node_exporter + restic + ansible   │
          └──────────────────────────────────────┘
```

Ключевые факты:

- **Один landing-VM** для публичного сайта — не горизонтально масштабируется, это side-project.
- **Один bastion-VM** — точка входа для всех админ-подключений и AmneziaWG-концентратор (UDP/443, обфускация против РКН-DPI). В Path A бастион совмещён с landing-VM (TCP/443 у Caddy + UDP/443 у AmneziaWG — разные протоколы, не конфликтуют).
- **Бэкапы** — Yandex Object Storage через `restic` (см. `technical/0_Common/ansible/playbooks/backup_install.yml`).
- **Мониторинг** — Prometheus scrape'ает всех клиентов через AmneziaWG-оверлей.

---

## Порядок развёртывания с нуля

Новичок, который впервые видит репо и хочет поднять всё от начала — идёт по этому списку.

### Этап A. Локальная разработка (0 ₽, 20 мин)

Нужно просто увидеть лендинг на экране. Ничего в облако не выкатывается.

→ [`local_dev.md`](local_dev.md)

**Результат:** `http://localhost:3000` открывает лендинг, форма заявки работает, заявки попадают в локальную MongoDB.

### Этап B. Продакшен-лендинг (~4 000 ₽/мес OPEX, 4–6 часов)

Нужен, когда решил: «стартую бизнес, хочу публичный сайт на `msp-claude.online`». Не раньше спринта 2 (см. [`docs/roadmap/etape_4_sprints.md`](../roadmap/etape_4_sprints.md)).

→ [`landing_production.md`](landing_production.md)

**Что понадобится:**

- Аккаунт [Yandex Cloud](https://cloud.yandex.ru/) + привязанная карта.
- Домен (покупается на `reg.ru` или аналоге, ~600 ₽/год).
- SSH-ключ (`ssh-keygen -t ed25519`).
- `terraform` ≥ 1.5, `ansible` ≥ 2.15, `yc` CLI.

**Итог:** `https://msp-claude.online` работает с валидным SSL, форма заявки пишет в MongoDB, уведомления приходят в Telegram и/или MAX (по выбору, `ALERT_CHANNELS=max,telegram` — см. [`docs/MAX_SETUP.md`](../MAX_SETUP.md)), Prometheus собирает метрики, Alertmanager шлёт алёрты в те же мессенджеры.

### Этап C. Первый клиент (онбординг)

Запускается после подписания контракта с конкретным клиентом. Никогда не раньше этапа B.

→ [`tenant_onboarding.md`](tenant_onboarding.md)

**Основные шаги:**

1. `tenant_add.sh` на bastion — создать AmneziaWG-peer (UDP/443 с обфускацией).
2. `ansible-playbook playbooks/site.yml --limit <client> --tags tier_bronze`.
3. Установить `restic` и запустить первый бэкап.
4. Передать welcome-package (см. `docs/onboarding/welcome_package.md`).
5. Первый weekly-sync через 7 дней.

---

## Безопасность

Полный гид по работе с секретами — [`secrets_management.md`](secrets_management.md)
(Vaultwarden, Yandex Lockbox, ротация, что не коммитить, pre-commit hook).
Не дублируем здесь, чтобы не разъезжалось.

---

## Связанные документы

- [`../roadmap/etape_4_sprints.md`](../roadmap/etape_4_sprints.md) — порядок спринтов (когда что развёртывать).
- [`../onboarding/day_1_7_runbook.md`](../onboarding/day_1_7_runbook.md) — первые 7 дней клиента.
- [`../runbooks/`](../runbooks/) — R-01…R-11 реагирование на инциденты.
- [`../checklists/quarterly.md`](../checklists/quarterly.md) — в том числе DR-drill (см. `technical/0_Common/scripts/dr_drill.sh`).
