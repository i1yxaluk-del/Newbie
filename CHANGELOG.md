# CHANGELOG

## v5.0 — 2026-05 · "PowerShell-first SOPs + Yandex-friendly mail"

Полная переработка SOP-инструкций под администратора, работающего с
**Windows 10**, и приведение почтового стека Yandex Cloud в соответствие
с реальной политикой YC по TCP/25.

### Changed (SOPs)

- `technical/1_Bronze/EXECUTOR/SOP_executor_bronze.md`
- `technical/1_Bronze/CLIENT/SOP_client_bronze.md`
- `technical/2_Silver/EXECUTOR/SOP_executor_silver.md`
- `technical/2_Silver/CLIENT/SOP_client_silver.md`
- `technical/3_Gold/EXECUTOR/SOP_executor_gold.md`
- `technical/3_Gold/CLIENT/SOP_client_gold.md`

Все шесть SOP переведены на PowerShell-first формат: команды на
Win10-станции выполняются в PowerShell 5.1/7, а Linux-команды
запускаются как `bash`-блоки через OpenSSH client (`ssh root@srv 'bash …'`
или `... | ssh ... bash -s`). Управление Windows-серверами клиента —
через `Invoke-Command` (WinRM) или RDP. Серверная архитектура
(Yandex Cloud, Ubuntu 22.04, WireGuard, Docker Compose, Prometheus,
Grafana, Loki, Wazuh, Puppet, Ansible) не изменилась.

- `technical/3_Gold/SOP_gold_complete.md` — добавлено явное
  предупреждение об устаревании и ссылки на актуальные v3.0 SOPs.

- `technical/README.md` — добавлен баннер про PowerShell-first и
  Stalwart submit-only режим, обновлена дата ревизии.

### Changed (Stalwart Mail / deploy/yandex/)

Yandex Cloud блокирует TCP/25 на публичных IP VPC. Все upstream-документы
обновлены, чтобы соответствовать этому ограничению:

- `deploy/yandex/docker-compose.yml` — порт `25:25` удалён, активные
  порты: **465 (SMTPS submission)**, **587 (STARTTLS submission)**,
  143/993 (IMAP/IMAPS), 4190 (ManageSieve), 127.0.0.1:8080 (Admin WebUI).
- `deploy/yandex/cloud-init.yaml` — `ufw allow 25/tcp` убран, добавлены
  правила 465/587/143/993/4190 и комментарий о submit-only режиме.
- `deploy/yandex/deploy.ps1` — security-group `msp-sg` пересоздана с
  inline-правилами для 465/587/143/993/4190 (без 25). Финальный вывод
  скрипта рекламирует submit-only режим и smarthost.
- `deploy/yandex/README.md` — переписаны разделы Stalwart,
  SMTP-настройки Grafana/Wazuh/Alertmanager (`stalwart:587`).
- `deploy/yandex/STALWART_RELAY_MODE.md` — **новый документ**: полное
  руководство по submit-only режиму, smarthost (Yandex 360 / Mailgun /
  Brevo), внешним MX-провайдерам (Yandex 360, Mailgun routes,
  Cloudflare Email Routing), DNS-записям, верификации и rollback'у на
  TCP/25 (если YC снимет ограничение).

---

## v4.1 — 2026-04 · "Materialization"

Все 53 артефакта Марафона 3.1–3.5 материализованы как реальные файлы
репозитория. В v4.0 был только README; в v4.1 — полный pack.

### Added

**Analysis (7 файлов):**
- `analysis/unit_economics.md` — юнит-экономика Bronze/Silver/Gold, LTV/CAC.
- `analysis/cac_model.md` — 3 канала (HH, 1С-франшиза, контент), blended CAC.
- `analysis/ltv_model.md` — 36-месячный conservative cap, NRR, churn.
- `analysis/finmodel_m1_m24.md` — помесячная финмодель до break-even.
- `analysis/icp_profiles.md` — 3 ICP + анти-ICP + 0–100 скоринг.
- `analysis/addon_catalog.md` — 10 разовых услуг с margin-target.
- `analysis/discount_policy.md` — max 10%, allowed/forbidden cases.

**Landing (9):**
- `frontend/src/components/sections/CTAForm.jsx` — form с consent (152-ФЗ), honeypot, Yandex SmartCaptcha (optional).
- `frontend/public/index.html` — enhanced meta, JSON-LD LocalBusiness + FAQPage, OG/Twitter cards.
- `frontend/public/docs/privacy.html`, `offer.html`, `sla.html` — юридика.
- `docs/landing/seo_strategy.md`, `ab_testing.md`, `blog_plan.md`, `yandex_metrika_goals.md`.

**Operations (22):**
- `docs/sales/funnel_6_stages.md`, `bant_q_script.md`, `email_templates.md`.
- `docs/onboarding/pre_onboarding_checklist.md`, `day_1_7_runbook.md`, `welcome_package.md`.
- `docs/runbooks/README.md` + R-01…R-10 (ransomware, access-loss, backup, 1С, AD, disk, SSL, VPN, password, patches).
- `docs/checklists/{weekly,monthly,quarterly}.md`.
- `docs/post_mortem_template.md` — blameless post-mortem.
- `docs/burnout_guard.md` — hard limits + weekly burnout score.

**Infrastructure (9):**
- `backend/server.py` — rate-limit per-IP, honeypot check, consent (152-ФЗ), optional Yandex SmartCaptcha server-side verify, `/metrics` Prometheus.
- `backend/.env.example` — полный шаблон переменных.
- `backend/requirements.txt` — +`prometheus_client>=0.20`.
- `deploy/nginx/mspshield.conf` — production reverse-proxy (SSL, CSP, rate-limit zones).
- `deploy/docker-compose.yml` + `Dockerfile.{backend,frontend}` — dev/staging стенд.
- `deploy/vaultwarden/` — secrets store deployment.
- `infra/terraform/` — Yandex Cloud baseline (VPC, landing+bastion VMs, S3 backups, IAM).
- `technical/0_Common/wireguard/` — bootstrap + tenant_add scripts.
- `technical/0_Common/ansible/` — inventory, playbooks (site, backup_install, patch_non/disruptive).
- `technical/0_Common/monitoring/` — Prometheus config + alert rules (common, backups, ssl, ad) + Alertmanager.
- `technical/0_Common/scripts/dr_drill.sh`, `monthly_report.py`.
- `docs/runbooks/R-11.md` — DR drill runbook.

**Hiring (6 + 12):**
- `docs/hiring/junior_jd.md`, `screening_call.md`, `test_task.md`, `technical_interview.md`, `offer_and_ndca.md`.
- `docs/training/README.md` + `week_01.md` … `week_12.md` — 12-недельная программа.
- `technical/0_Common/scripts/rotate_junior_access.sh` — promote/revoke/rotate.

### Changed

- `README.md` полностью переписан под реальную файловую структуру и содержит клик-ссылку на каждый из 53 артефактов.
- `backend/server.py` — версия API 3.1.0 → 4.1.0. Добавлены поля `consent`, `website` (honeypot), `smartcaptcha_token` в `LeadCreate`. Sensitive поля не персистятся.
- `backend/requirements.txt` — добавлен `prometheus_client`.

### Not changed (по дизайну)

- Production-инфраструктура НЕ развёрнута (terraform apply, ansible-playbook site.yml не запускались).
- Wazuh / Kaspersky Security Center не устанавливались.
- Live-тесты CAPTCHA не проводились (требуется реальный SITE_KEY / SERVER_KEY).

---

## v4.0 — 2026-03

- README-only релиз: стратегический план Марафона 3.1–3.5 как индекс + roadmap + навигация по репозиторию.
- Тег `v4.0`, PR #1 смёржен в `main`.

---

## v3.1 (и ранее)

- Базовая имплементация React + FastAPI + MongoDB, админ-панель, 12 секций лендинга.
- Playbook Bronze / Silver / Gold в `technical/`.
- Договоры в `contracts/`.
- Анализ рынка в `analysis/market_analysis.md`.
