# MSPShield

> **Managed IT Services для СМБ в РФ.** Мониторинг 24/7 · автоматические
> бэкапы · реакция по SLA · 152-ФЗ · импортозамещение.
>
> Лендинг на [`msp-claude.online`](https://msp-claude.online) + FastAPI-бэкенд
> + Kaiten CRM + многоуровневая инфра (Bronze / Silver / Gold) на Yandex Cloud.

---

## Куда дальше — 4 маршрута

Выбери, кто ты, и читай только нужную ветку. Не нужно знать весь репо.

| Я хочу… | Иду в… | Время |
|---|---|---|
| 🚀 **Развернуть сайт и инфру** (от нуля до прод-лендинга) | [`docs/deployment/README.md`](docs/deployment/README.md) | 20 мин → 6 ч |
| 🛠 **Обслуживать клиентов по тарифам** (Bronze / Silver / Gold) | [`technical/README.md`](technical/README.md) | по тарифу |
| 🎓 **Обучиться с нуля как Junior-инженер** (12 недель) | [`docs/training/README.md`](docs/training/README.md) | 12 нед |
| ✏️ **Редактировать тексты, тарифы, иконки лендинга** (без кода) | [`docs/EDITING.md`](docs/EDITING.md) | 15 мин |

Каждый из этих README — **канонический источник** по своей теме. Если
видишь дубль или противоречие — это баг, заводи issue.

### Сопутствующее

| Тема | Где |
|---|---|
| Админ-гид лендинга (поднять локально, починить форму, посмотреть лиды) | [`docs/LANDING_ADMIN_GUIDE.md`](docs/LANDING_ADMIN_GUIDE.md) |
| Реактивные runbooks (R-01..R-11: ransomware, backup, SSL, VPN, DR) | [`docs/runbooks/README.md`](docs/runbooks/README.md) |
| Управление секретами (Vaultwarden + Yandex Lockbox) | [`docs/deployment/secrets_management.md`](docs/deployment/secrets_management.md) |
| CRM Kaiten (воронка, доски, custom fields) | [`docs/KAITEN_SETUP.md`](docs/KAITEN_SETUP.md) |
| Алерты в MAX-мессенджер (РФ-альтернатива Telegram) | [`docs/MAX_SETUP.md`](docs/MAX_SETUP.md) |
| Соответствие 152-ФЗ + импортозамещение | [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) |
| Roadmap (Этап 4: 12 спринтов × 2 нед) | [`docs/roadmap/README.md`](docs/roadmap/README.md) |
| Договоры (Bronze / Silver / Gold) | [`contracts/README.md`](contracts/README.md) |

---

## Тарифы (главное)

| Тариф | Цена | Серверов | SLA P1 | Что входит | Мастер-гайд |
|---|---:|---|---|---|---|
| **Bronze** | от 25 000 ₽/мес | 1–5 | ≤ 4 ч (раб. время) | Prometheus + restic + AmneziaWG + Telegram/MAX-алерты | [`technical/1_Bronze/Bronze.md`](technical/1_Bronze/Bronze.md) |
| **Silver** | от 50 000 ₽/мес | 6–15 | ≤ 2 ч | Bronze + Loki + Puppet + AD/GPO + Ansible | [`technical/2_Silver/Silver.md`](technical/2_Silver/Silver.md) |
| **Gold** | от 85 000 ₽/мес | 16–30 | ≤ 1 ч, 24/7 | Silver + Wazuh SIEM + Kaspersky EDR + osTicket | [`technical/3_Gold/Gold.md`](technical/3_Gold/Gold.md) |

Юнит-экономика, маржа, LTV/CAC: [`analysis/unit_economics.md`](analysis/unit_economics.md).
Бизнес-модель и upsell: [`technical/BUSINESS_MODEL.md`](technical/BUSINESS_MODEL.md), [`technical/ADDONS.md`](technical/ADDONS.md).

---

## Технический стек (одной таблицей)

| Слой | Технология | Где живёт |
|---|---|---|
| **Frontend** | React 19 + Tailwind + shadcn/ui | [`frontend/`](frontend/) |
| **Backend** | FastAPI 0.110 + Motor (async MongoDB) | [`backend/`](backend/) |
| **БД** | MongoDB 7 | контейнер в [`deploy/yandex/docker-compose.yml`](deploy/yandex/docker-compose.yml) |
| **Reverse proxy / TLS** | Caddy (Path A) или Nginx + Certbot (Path B) | [`deploy/yandex/Caddyfile`](deploy/yandex/Caddyfile), [`deploy/nginx/mspshield.conf`](deploy/nginx/mspshield.conf) |
| **Облако** | Yandex Cloud (VPC + Compute + Object Storage) | [`infra/terraform/`](infra/terraform/) |
| **VPN** | AmneziaWG, UDP/443, обфускация против РКН-DPI | [`technical/0_Common/amneziawg/`](technical/0_Common/amneziawg/) |
| **Мониторинг** | Prometheus + Grafana + Alertmanager (+ Loki Silver+, Wazuh Gold) | [`technical/0_Common/monitoring/`](technical/0_Common/monitoring/) |
| **Бэкап** | restic → Yandex Object Storage (AES-256) | [`technical/0_Common/ansible/playbooks/backup_install.yml`](technical/0_Common/ansible/playbooks/backup_install.yml) |
| **Mail (исходящий)** | Stalwart → Yandex Cloud Postbox (587 STARTTLS) | [`deploy/yandex/STALWART_RELAY_MODE.md`](deploy/yandex/STALWART_RELAY_MODE.md) |
| **Secrets** | Vaultwarden (self-hosted, бесплатный) | [`deploy/vaultwarden/`](deploy/vaultwarden/) |
| **CRM** | Kaiten (REST API) | [`docs/KAITEN_SETUP.md`](docs/KAITEN_SETUP.md) |
| **Captcha** | Yandex SmartCaptcha (опционально) | `SMARTCAPTCHA_SERVER_KEY` в [`backend/.env.example`](backend/.env.example) |

---

## Локальный запуск (3 команды)

```bash
git clone https://github.com/i1yxaluk-del/Newbie.git && cd Newbie
docker compose -f deploy/docker-compose.yml up -d mongo
cd backend && cp .env.example .env && pip install -r requirements.txt && uvicorn server:app --reload --port 8001 &
cd ../frontend && cp .env.example .env && yarn install && yarn start
```

Открыть: `http://localhost:3000` (лендинг), `http://localhost:3000/admin/leads` (админка),
`http://localhost:8001/docs` (Swagger), `http://localhost:8001/metrics` (Prometheus).

Полная инструкция и переменные окружения — в [`docs/deployment/local_dev.md`](docs/deployment/local_dev.md) и [`backend/.env.example`](backend/.env.example).

---

## Структура репо (верхний уровень)

```
Newbie/
├── README.md              ← вы здесь (только навигация)
├── CHANGELOG.md           ← история версий
│
├── frontend/              React 19 SPA-лендинг + админка
├── backend/               FastAPI + Motor/MongoDB
├── analysis/              юнит-экономика, ICP, CAC/LTV, финмодель
├── contracts/             договоры клиент/MSP
├── scripts/               kaiten_bootstrap, seed_test_lead и т.п.
│
├── deploy/
│   ├── yandex/            Path A: единая VM, Caddy+Docker, deploy.ps1
│   ├── vaultwarden/       self-hosted secrets store
│   ├── nginx/             nginx-конфиг для Path B
│   └── docker-compose.yml dev/staging стенд
│
├── infra/terraform/       Yandex Cloud baseline (VPC + landing + bastion + S3)
│
├── technical/             ← обслуживание клиентов
│   ├── README.md          навигатор по тарифам
│   ├── BUSINESS_MODEL.md  экономика, ADDONS, SCALING
│   ├── 0_Common/          межтарифные компоненты (Ansible, monitoring, AmneziaWG)
│   ├── 1_Bronze/          Bronze SOPs (1–5 серверов)
│   ├── 2_Silver/          Silver SOPs (80–300 сотр.)
│   └── 3_Gold/            Gold SOPs (SIEM/Wazuh)
│
└── docs/
    ├── deployment/        развёртывание (A: local, B: prod, C: tenant)
    ├── training/          12-недельная программа Junior
    ├── runbooks/          R-01..R-11 на инциденты
    ├── checklists/        weekly / monthly / quarterly
    ├── onboarding/        приём нового клиента (день 1–7)
    ├── sales/             воронка, BANT-Q, email-шаблоны
    ├── landing/           SEO, A/B, blog-план
    ├── hiring/            JD + screening + test task + interview
    ├── roadmap/           Этап 4: 12 спринтов
    ├── audit/             исторические отчёты (v4.1_inventory, v4.2, v4.3, v4.4)
    ├── LANDING_ADMIN_GUIDE.md  ← про сайт (не про клиентов)
    ├── EDITING.md         редактирование контента лендинга
    ├── KAITEN_SETUP.md    настройка CRM
    ├── MAX_SETUP.md       MAX-мессенджер для алертов
    ├── COMPLIANCE.md      152-ФЗ + импортозамещение
    └── post_mortem_template.md
```

---

## Что нового

См. [`CHANGELOG.md`](CHANGELOG.md). Последние крупные изменения:

- **v4.5** — рестрyктура навигации READMEs (1 канонический README на задачу).
- **v4.4** — миграция WireGuard → **AmneziaWG** (UDP/443, обфускация против РКН-DPI).
- **v4.3** — outbound mail через **Yandex Cloud Postbox** (587 STARTTLS).
- **v4.2** — домен **`msp-claude.online`**, 3 канонических ящика `admin@/sales@/alert@`.
- **v4.1** — материализация 53 артефактов Марафона 3.1–3.5 (см. [`docs/audit/v4.1_inventory.md`](docs/audit/v4.1_inventory.md)).

---

## Что НЕ коммитим

Один источник правды — [`docs/deployment/secrets_management.md`](docs/deployment/secrets_management.md).

Кратко: `*.env`, `*.tfvars`, `*.tfstate*`, `*.key`, `*.pem`, любые токены/пароли/SSH-ключи. На каждом коммите:

```bash
git diff --cached | grep -iE "(TOKEN|PASSWORD|SECRET|PRIVATE.*KEY)" && echo STOP || echo OK
```

Найдено — `git reset HEAD <file>` и исправить.
