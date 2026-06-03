# CHANGELOG

## v5.4 — 2026-06-03 · "Project audit + doc truth-up"

Полный аудит проекта (60+ .md, 100 коммитов, 37 PR с мая по июнь 2026).
Выявлено 9 расхождений между документацией и реальным кодом. Этот релиз
синхронизирует доки с тем, что фактически закоммичено в `main`.

### Changed

- **`README.md`** · таблица "Технический стек" — строка "Mail (исходящий)":
ссылка обновлена с `STALWART_RELAY_MODE.md` (deprecated с v4.3) на
актуальный мейл-стек `deploy/yandex/README.md` → раздел Postbox.
Описание унифицировано: "Yandex Cloud Postbox (MSA :465, implicit TLS)" —
без упоминания Stalwart, который больше не используется в проде.
- **`docs/audit/v4.1_inventory.md`** · добавлен баннер "исторический snapshot,
не отражает текущее состояние репо" со ссылкой на этот CHANGELOG.

### Deprecated

- **`deploy/yandex/STALWART_RELAY_MODE.md`** · помечен deprecated-баннером
сверху. Файл сохранён для истории и rollback, но в проде не используется
с v4.3 (Postbox direct).

### Added

- **`docs/audit/v5.4_audit_report.md`** · полный отчёт аудита: 9 gaps (3C/4M/2L),
методология, инвентарь 60+ файлов, план исправлений. Audit trail для
будущих ревью.

### Закрытые gaps аудита

- **C1** CHANGELOG stale (отсутствовали v5.3 + v5.4) → добавлены обе версии.
- **C2** README stack table ссылалась на deprecated файл → исправлено.
- **C3** v4.1_inventory без disclaimer → баннер добавлен.
- **M4** STALWART_RELAY_MODE без deprecation-маркера → баннер добавлен.

### Open gaps (не закрываются в этом релизе)

- **M1** ~17 коммитов 2 июня 2026 закоммичены прямо в main без PR
(брендирование, обучение wk3-4) — фиксируется политикой "PR-only с v5.5".
- **M2** Skeleton-файлы `docs/training/week_05.md` … `week_12.md` —
расписаны в roadmap, фактическое наполнение — Этап 4 спринт 8-12.
- **M3** R-08 runbook упоминает WireGuard вместо AmneziaWG (миграция v4.4
не дошла до runbook) — фикс в v5.5.
- **L1** Пустые директории `docs/contracts_v2/` — кандидат на удаление.
- **L2** Несколько cosmetic-опечаток в README (Kaiten/Kaizen, MongoDb,
msps**s**heild.conf и т.п.) — отдельный proof-reading-pass в v5.5.

---

## v5.3 — 2026-06-02..03 · "Monitoring stack, Postbox :465 fix, training wk3-4, branding"

Серия коммитов 2-3 июня 2026 прямо в `main` (без PR — git push from devin/lindy).
Этот раздел задним числом фиксирует, что фактически попало в репо за эти два дня.

### Added (monitoring stack)

- **Grafana dashboards** (`technical/0_Common/monitoring/grafana/dashboards/`):
- `infra_overview.json` — CPU/RAM/Disk/Network/Docker по всем VM.
- `restic_backup.json` — heatmap последнего успешного бэкапа на хост,
  точное соответствие виджету на лендинге.
- `amneziawg_vpn.json` — handshake-возраст, RX/TX, активные peers.
- `caddy_postbox.json` — TLS-сертификаты Caddy + Postbox queue size.
- **Prometheus rules** (`technical/0_Common/monitoring/prometheus/rules/`):
- `backup_alerts.yml` — 6 правил: bronze/silver/gold SLA по бэкапам,
  verify failure, restore-test missed, age > 25 h.
- `vpn_alerts.yml` — AmneziaWG handshake old > 5 min, peer down.
- **Restic backup textfile collector** — `technical/0_Common/scripts/restic_metrics.sh`,
systemd path-unit публикует метрики в `/var/lib/node_exporter/textfile/`
(restic не имеет нативного Prometheus-экспортера).

### Fixed (Postbox)

- **Postbox `:587 STARTTLS` отбрасывает соединения** → переход на
**`:465 implicit TLS`** во всех клиентах:
Grafana (`GF_SMTP_HOST`), Alertmanager (`smtp_smarthost`), Vaultwarden
(`SMTP_PORT=465`, `SMTP_SECURITY=force_tls`). Документировано в
`deploy/yandex/README.md` и `STALWART_RELAY_MODE.md` (deprecated).
- Stalwart как промежуточный relay в проде **не используется** — все
клиенты ходят на Postbox напрямую. Stalwart-конфиги оставлены для
возможного rollback'а.

### Added (AmneziaWG best practices)

- `technical/0_Common/amneziawg/README.md` — раздел "Production best practices":
rotation peer-ключей раз в 90 дней, мониторинг handshake-возраста,
чек-лист перед добавлением tenant'а, troubleshooting BOM/MTU/firewall.

### Added (training week 3-4)

- `docs/training/week_03.md` — "Linux fundamentals: процессы, systemd, journald".
- `docs/training/week_04.md` — "Docker & docker-compose: образы, тома, сети".
(week_05..week_12 пока skeleton'ы — расписаны в roadmap.)

### Added (branding)

- `frontend/src/theme/brand.js` — единая палитра/типографика MSPShield
(была разбросана по компонентам).
- Обновлены 4 компонента на использование `brand.colors.primary` вместо
hard-coded `#0066cc`.

### Note

Все коммиты этого релиза попали в `main` напрямую (PR-токен не имел
`refs:write` scope на момент пуша). Политика "PR-only" вводится с v5.5.

---

## v4.5 — 2026-05-22 · "READMEs cleanup — один канонический README на задачу"

После серии PR #43–#49 в репо накопилось 6 «корневых» README, каждый
позиционировался как «начни здесь», и они пересекались на 50–80%.
Реорганизация: один канонический README на тему, чёткие 4 маршрута
по ролям, навигация по тарифам в `technical/README.md`.

### Changed

- **`README.md`** сокращён с 561 → 160 строк. Теперь только обзор +
4 маршрута (deploy / tariffs / training / landing-edit) + таблица
тарифов + стек + локальный запуск + структура.
- **`technical/README.md`** переписан как **канонический tariff-навигатор**.
Удалены дубли по ролям (training/runbooks теперь в своих README).
- **`docs/deployment/README.md`** — добавлен явный выбор Path A vs Path B,
удалена дублирующая секция «что не коммитить» (теперь в `secrets_management.md`).
- **`docs/training/README.md`** — добавлены cross-link'и на runbooks /
checklists / troubleshooting / secrets, фикс WireGuard → AmneziaWG.
- **`deploy/yandex/README.md`** — хедер «это deep-dive Path A», AmneziaWG/Postbox.
- **`docs/runbooks/README.md`** — R-08 переименован WireGuard → AmneziaWG
(унификация с PR #47).

### Renamed

- **`docs/JUNIOR_GUIDE.md`** → **`docs/LANDING_ADMIN_GUIDE.md`** — старое
название путало: этот файл про сайт MSPShield (поднять локально,
починить форму, посмотреть лиды в Kaiten), а не про обслуживание
клиентских серверов. Реальный Junior-слой живёт в `docs/training/`.

### Added

- **`docs/audit/v4.1_inventory.md`** — перенесён список 53 артефактов
Марафона 3.1–3.5 + DoD из корневого README. Это исторический snapshot,
не нужен в ежедневной навигации.

### Removed

- **`docs/lifecycle/`** (570 строк) — каталог удалён целиком. 80% содержимого
дублировало `docs/deployment/landing_production.md` и `LANDING_ADMIN_GUIDE.md`,
устаревшая версия v4.2 (до AmneziaWG/Postbox). «Friendly tone» — теперь
внутри dedicated README'ев.

### Импакт

- −950 строк дублей.
- Один канонический источник на каждую задачу (нет противоречий).
- Junior понимает «куда идти» по своей роли за 30 секунд.

---

## v5.2 — 2026-05-26 · "AmneziaWG + Vaultwarden + Restic backup — postmortem"

Развёртывание AmneziaWG VPN, Vaultwarden secret store и restic backup на
single-VM в Yandex Cloud. 7 инцидентов во время деплоя, все разрешены,
все уроки закодированы в репозитории.

### Added

- **AmneziaWG VPN** (`awg0`, UDP/443) вместо WireGuard — РКН-DPI блокирует
стандартный WG handshake. Обфускация (Jc/Jmin/Jmax/S1/S2/H1..H4).
- `technical/0_Common/amneziawg/` — bootstrap + tenant_add скрипты
- VPN subnet `10.9.0.0/24` (не 10.10.0.0/16 — конфликт с YC internal 10.10.0.0/24)
- Endpoint `bastion.msp-claude.online:443`
- **Vaultwarden** на той же VM (не отдельная VM), за Caddy reverse proxy.
- `deploy/yandex/docker-compose.yml` — сервис `vaultwarden` (127.0.0.1:8180)
- `deploy/yandex/Caddyfile` — блок `vault.msp-claude.online`
- `deploy/vaultwarden/` — обновлён README (single-VM), убран SMTP из compose
- **Restic backup** — S3 bucket `mspshield-backups-prod`, SA `restic-backup-sa`,
systemd timer (02:00 daily). Первый бэкап 1278 файлов / 191 MB, test-restore PASS.
- **YC SA + S3 ключи** для restic (`storage.admin` на folder)
- **Caddy HTTP3 disabled** — `servers :443 { protocols h1 h2 }` в global block

### Fixed (deployment postmortem — 7 incidents)

- **I1 (VPN subnet conflict):** `awg_bootstrap.sh` default `10.10.0.1/16`
конфликтует с YC internal `10.10.0.0/24` на eth0 → `RTNETLINK answers:
Address already in use`. Fix: VPN subnet → `10.9.0.0/24`. Updated in
15 files: bootstrap, tenant_add, ansible roles, docs, prometheus, nginx.
- **I2 (Caddy QUIC vs AmneziaWG):** Caddy v2.6+ включает HTTP/3 (QUIC)
на UDP/443 по умолчанию → AmneziaWG не может bind. Fix: `servers :443
{ protocols h1 h2 }` в Caddyfile global block.
- **I3 (UFW 443/udp missing):** AmneziaWG на UDP/443, но UFW правило
только для 443/tcp. Fix: `ufw allow 443/udp comment 'AmneziaWG VPN'`.
Already present in `cloud-init.yaml` and `setup_awg_bastion.sh`.
- **I4 (Vaultwarden SMTP crash):** Vaultwarden 1.36.0 падает при неполных
SMTP vars (SMTP_HOST set, SMTP_FROM empty). Fix: убрать SMTP env vars
из compose — настроить позже через /admin когда Stalwart relay заработает.
- **I5 (AWG client config BOM):** AmneziaWG Windows client не читает
конфиг с UTF-8 BOM (`\xEF\xBB\xBF`) — "Unable to load configuration".
Fix: `sed -i '1s/^\xEF\xBB\xBF//'` в `tenant_add.sh`; записывать конфиг
без BOM (`UTF8Encoding($false)` в PowerShell).
- **I6 (Vaultwarden separate VM vs single VM):** README предписывал
отдельную VM + `certbot --nginx`. Реальность: одна VM + Caddy. Fix:
обновлён README, Caddyfile, docker-compose.
- **I7 (Restic env.sh permissions):** install script создаёт env.sh как
root:root 0600 → `source` от ubuntu user fails. Fix: `sudo chmod 644`
перед source, потом вернуть 600.

### Changed

- VPN overlay subnet: `10.10.0.0/16` → `10.9.0.0/24` (15 files)
- `deploy/vaultwarden/docker-compose.yml` — removed SMTP vars, updated comment
- `deploy/vaultwarden/README.md` — single-VM deployment, Caddy auto-HTTPS
- `deploy/yandex/Caddyfile` — disabled QUIC, added vault.msp-claude.online
- `deploy/yandex/docker-compose.yml` — added vaultwarden service
- `technical/0_Common/amneziawg/tenant_add.sh` — BOM strip, 10.9.0.0/24
- `technical/0_Common/amneziawg/awg_bootstrap.sh` — default 10.9.0.1/24

## v5.1 — 2026-05 · "Deployment lessons from real prod deploy"

Кодификация 12 уроков из реального деплоя одиночной preemptible-VM в Yandex
Cloud + проброса метрик в Grafana (май 2026). См. PR #41, PR #42 и audit
отчёт `repo_audit_deployment_lessons.md` (не в репо).

### Fixed (PR #41 — `fix: deployment lessons from real deploy`)

- **L1 (Docker overlay2):** Docker 29+ на Ubuntu 22.04 по умолчанию
использует overlayfs storage driver → cAdvisor не видит контейнеры.
Принудительно `/etc/docker/daemon.json: {"storage-driver":"overlay2"}`
через cloud-init **до** первого старта Docker.
- `deploy/yandex/cloud-init.yaml`, Bronze SOP §3, Gold SOP, Gold complete.
- **L2 (cAdvisor v0.49.1 → v0.51.0):** v0.49 не поддерживает overlayfs.
- `technical/0_Common/docker/.env.example`, `deploy/yandex/monitoring/`.
- **L3 (cAdvisor mount):** `/var/lib/docker/` нужно мапить как
`/rootfs/var/lib/docker:ro` + bind `docker.sock`.
- **L4 (cAdvisor `--disable_metrics`):** длинный список ломает запуск.
Сокращено до `percpu,sched,tcp,udp`.
- **L5 (preemptible + static IP):** preemptible VM меняет IP при рестарте,
+ `core-fraction 20%` недоступен для 2 vCPU (минимум 50%).
- `deploy/yandex/deploy.ps1` (флаг `-UseStaticIp`), Bronze SOP §2.2,
  `docs/audit/v4.2_tariff_review.md` (новый тариф ~1 676 ₽/мес).
- **L6 (SSH host keys на preemptible):** `-o StrictHostKeyChecking=no`
`-o UserKnownHostsFile=NUL` (/dev/null на Linux) во всех SSH/SCP.
- Helpers `msp-ssh`/`msp-bash`, ssh-config примеры.
- **L7 (PS 5.1 + yc stderr):** обёртка `cmd /c "yc ... 2>&1"`.
- `deploy/yandex/deploy.ps1`, Bronze/Silver/Gold SOP (helper `Invoke-Yc`).
- **L8 (Caddy + опечатка домена):** silent fallback на staging
Let's Encrypt CA при NXDOMAIN. Фикс — `acme_ca` global-блок в Caddyfile.

### Fixed (PR #42 — мониторинг через Docker DNS)

- **M1 (backend bind):** `127.0.0.1:8001` → `0.0.0.0:8001`, чтобы
Prometheus в отдельном compose-стеке мог скрейпить backend.
Порт остаётся закрыт UFW снаружи.
- **M2 (внешняя Docker-сеть):** `monitoring/docker-compose.yml` подключён
к `msp_default` (external: true) для Docker DNS.
- **M3 (DNS-имя вместо IP):** Prometheus target
`mspshield-backend` → `backend:8001` (а не `172.17.0.1:8001`).
- **M4:** дублирующийся `networks:` ключ в YAML объединён.

### Closed in this PR (v5.1)

- **P0** `infra/terraform/cloud-init/landing.yaml` — добавлен write_files
блок с `/etc/docker/daemon.json: {"storage-driver":"overlay2"}` (L1).
- **P1** `docs/deployment/landing_production.md` — добавлен баннер про
Path A vs Path B + врезки с уроками L1/L6/L8 в релевантные шаги.
- **P1** Bronze SOP — введён helper `Invoke-Yc`, все `yc` обёрнуты,
основной flow создания VM теперь включает резерв static IP +
`--preemptible`. Сломанная ссылка §5.4 на несуществующий
`monitoring-stack/` исправлена на `technical/0_Common/docker/...`.
- **P1** Silver SOP — `yc` обёрнут в `Invoke-Yc`, cost table обновлена
(`Bastion VM 2 vCPU 5%` → `50%`, ~600 ₽ → ~750 ₽).
- **P2** Gold SOP — `yc` обёрнут, cost table обновлена.
- **P2** Ansible inventory шаблон + `onboard_client.sh` — добавлен
`UserKnownHostsFile=/dev/null` в `ansible_ssh_common_args`.
- **P2** `technical/0_Common/monitoring/prometheus.yml` — добавлен
комментарий про Path A (Docker DNS `backend:8001`) vs Path B
(host-loopback `127.0.0.1:8001`).
- **P3** `deploy/yandex/docker-compose.yml` header и `deploy/yandex/Caddyfile`
— обновлены устаревшие комментарии про `127.0.0.1:8001:8001`.

---

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
(Yandex Cloud, Ubuntu 22.04, AmneziaWG, Docker Compose, Prometheus,
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
- `technical/0_Common/amneziawg/` — bootstrap + tenant_add scripts.
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
