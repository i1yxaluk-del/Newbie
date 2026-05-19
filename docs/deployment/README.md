# Развёртывание MSPShield — оглавление

Инструкции по развёртыванию всего стека MSPShield на русском, от локальной разработки до первого клиента в продакшене.

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
                     │ WireGuard 10.10.0.0/16
                     │
          ┌──────────┴──────────────────────────┐
          │   mspshield-bastion (Yandex Cloud)  │
          │                                     │
          │   wg0 UDP 51820 ◄───┐               │
          │                     │               │
          │   Vaultwarden       │               │
          │   Prometheus/Alertmanager           │
          └─────────────────────┼───────────────┘
                                │ WireGuard 10.20.x.x
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
- **Один bastion-VM** — точка входа для всех админ-подключений и WireGuard-концентратор.
- **Бэкапы** — Yandex Object Storage через `restic` (см. `technical/0_Common/ansible/playbooks/backup_install.yml`).
- **Мониторинг** — Prometheus scrape'ает всех клиентов через WireGuard-оверлей.

---

## Порядок развёртывания с нуля

Новичок, который впервые видит репо и хочет поднять всё от начала — идёт по этому списку.

### Этап A. Локальная разработка (0 ₽, 20 мин)

Нужно просто увидеть лендинг на экране. Ничего в облако не выкатывается.

→ [`local_dev.md`](local_dev.md)

**Результат:** `http://localhost:3000` открывает лендинг, форма заявки работает, заявки попадают в локальную MongoDB.

### Этап B. Продакшен-лендинг (~4 000 ₽/мес OPEX, 4–6 часов)

Нужен, когда решил: «стартую бизнес, хочу публичный сайт на `mspshield.ru`». Не раньше спринта 2 (см. [`docs/roadmap/etape_4_sprints.md`](../roadmap/etape_4_sprints.md)).

→ [`landing_production.md`](landing_production.md)

**Что понадобится:**

- Аккаунт [Yandex Cloud](https://cloud.yandex.ru/) + привязанная карта.
- Домен (покупается на `reg.ru` или аналоге, ~600 ₽/год).
- SSH-ключ (`ssh-keygen -t ed25519`).
- `terraform` ≥ 1.5, `ansible` ≥ 2.15, `yc` CLI.

**Итог:** `https://mspshield.ru` работает с валидным SSL, форма заявки пишет в MongoDB, уведомления приходят в Telegram и/или MAX (по выбору, `ALERT_CHANNELS=max,telegram` — см. [`docs/MAX_SETUP.md`](../MAX_SETUP.md)), Prometheus собирает метрики, Alertmanager шлёт алёрты в те же мессенджеры.

### Этап C. Первый клиент (онбординг)

Запускается после подписания контракта с конкретным клиентом. Никогда не раньше этапа B.

→ [`tenant_onboarding.md`](tenant_onboarding.md)

**Основные шаги:**

1. `tenant_add.sh` на bastion — создать WireGuard-peer.
2. `ansible-playbook playbooks/site.yml --limit <client> --tags tier_bronze`.
3. Установить `restic` и запустить первый бэкап.
4. Передать welcome-package (см. `docs/onboarding/welcome_package.md`).
5. Первый weekly-sync через 7 дней.

---

## Безопасность и что НЕ коммитить

⛔ **НИКОГДА не попадает в git:**

- `backend/.env` (только `.env.example`).
- `infra/terraform/terraform.tfvars` (только `.tfvars.example`, которого пока нет — создаём локально).
- `infra/terraform/terraform.tfstate*` (state хранится в Yandex Object Storage backend, см. `main.tf`).
- Любые `*.key`, `*.pem`, `*.tgz` с данными клиентов.
- `/etc/wireguard/*.key` (даже в описаниях).
- Telegram bot-token, SMTP-пароль.

✅ **Что проверяется на каждом коммите:**

```bash
git diff --cached | grep -iE "(TOKEN|PASSWORD|SECRET|PRIVATE.*KEY)" && echo "STOP" || echo "OK"
```

Если попалось — `git reset HEAD <file>` и исправить.

---

## Связанные документы

- [`../roadmap/etape_4_sprints.md`](../roadmap/etape_4_sprints.md) — порядок спринтов (когда что развёртывать).
- [`../onboarding/day_1_7_runbook.md`](../onboarding/day_1_7_runbook.md) — первые 7 дней клиента.
- [`../runbooks/`](../runbooks/) — R-01…R-11 реагирование на инциденты.
- [`../checklists/quarterly.md`](../checklists/quarterly.md) — в том числе DR-drill (см. `technical/0_Common/scripts/dr_drill.sh`).
