# CHANGELOG

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
