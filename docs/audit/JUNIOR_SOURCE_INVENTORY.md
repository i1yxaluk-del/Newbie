# Карта пояснений в исходниках

Сформировано `scripts/audit_junior_readability.py`. Числа не доказывают понятность: комментарий может быть неверным, а JSON не поддерживает комментарии. Архив не входит в действующую выборку. Секреты и значения переменных не печатаются.

Проверено файлов: **361**; исключено архивных файлов: **70**.

## По каталогам

- `.github`: 1
- `backend`: 15
- `book`: 3
- `contracts`: 1
- `deploy`: 71
- `docs`: 5
- `frontend`: 104
- `infra`: 4
- `migration`: 30
- `scripts`: 18
- `services`: 14
- `technical`: 95

## Реестр файлов

| Путь | Строк | Комментариев | Python docstring | Python-функций | Повод для разбора |
|---|---:|---:|---:|---:|---|
| `.github/workflows/quality.yml` | 115 | 0 | 0 | 0 | нет комментариев/строк документации |
| `backend/auth.py` | 101 | 4 | 4 | 9 | Python без docstring: 34, 38, 69, 46, 49, 52 |
| `backend/integrations/__init__.py` | 0 | 0 | 0 | 0 | нет комментариев/строк документации |
| `backend/integrations/alertmanager.py` | 312 | 2 | 10 | 12 | Python без docstring: 78, 82, 238 |
| `backend/integrations/email.py` | 132 | 0 | 2 | 6 | Python без docstring: 40, 44, 48, 65, 90 |
| `backend/integrations/kaiten.py` | 238 | 0 | 11 | 10 | ручная проверка смысла |
| `backend/integrations/max.py` | 145 | 0 | 13 | 12 | ручная проверка смысла |
| `backend/integrations/telegram.py` | 92 | 0 | 3 | 5 | Python без docstring: 26, 35, 44 |
| `backend/integrations/webhook.py` | 50 | 0 | 1 | 2 | Python без docstring: 25, 29 |
| `backend/secure_server.py` | 263 | 3 | 13 | 11 | ручная проверка смысла |
| `backend/server.py` | 857 | 25 | 10 | 31 | Python без docstring: 223, 228, 233, 242, 249, 267, 337, 485, 490, 597, 652, 667, 672, 688, 737, 759, 774, 856, 127, 134, 142, 580 |
| `backend/tests/test_alertmanager.py` | 236 | 2 | 1 | 29 | Python без docstring: 17, 45, 52, 67, 72, 76, 82, 88, 93, 104, 111, 116, 122, 128, 133, 138, 144, 151, 158, 165, 168, 176, 181, 209, 225, 185, 189, 210, 226 |
| `backend/tests/test_kaiten_integration.py` | 98 | 0 | 1 | 11 | Python без docstring: 13, 35, 42, 47, 52, 62, 71, 79, 84, 96, 88 |
| `backend/tests/test_max_integration.py` | 130 | 2 | 1 | 13 | Python без docstring: 16, 23, 41, 53, 71, 76, 82, 89, 94, 102, 106, 112, 123 |
| `backend/tests/test_mspshield_api.py` | 282 | 8 | 3 | 27 | Python без docstring: 23, 30, 38, 45, 55, 85, 95, 106, 114, 118, 122, 133, 143, 147, 164, 174, 185, 193, 205, 216, 220, 233, 237, 248, 272 |
| `backend/tests/test_secure_delivery.py` | 93 | 0 | 1 | 11 | Python без docstring: 21, 26, 40, 52, 66, 74, 83, 90, 53, 77, 58 |
| `book/build_deep_book.py` | 162 | 2 | 1 | 4 | Python без docstring: 8, 24, 36, 10 |
| `book/verify_deep_book.py` | 13 | 0 | 0 | 0 | нет комментариев/строк документации |
| `book/verify_readability.py` | 13 | 0 | 0 | 0 | нет комментариев/строк документации |
| `contracts/build_contract_docx.py` | 59 | 1 | 1 | 3 | Python без docstring: 19, 21, 26 |
| `deploy/Dockerfile.backend` | 12 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/Dockerfile.frontend` | 33 | 14 | 0 | 0 | ручная проверка смысла |
| `deploy/alertmanager/alertmanager.yml` | 96 | 36 | 0 | 0 | ручная проверка смысла |
| `deploy/alertmanager/rules.example.yml` | 71 | 8 | 0 | 0 | ручная проверка смысла |
| `deploy/docker-compose.yml` | 39 | 6 | 0 | 0 | ручная проверка смысла |
| `deploy/mas/docker-compose.yml` | 46 | 6 | 0 | 0 | ручная проверка смысла |
| `deploy/mas/overrides/apply-overrides.sh` | 27 | 2 | 0 | 0 | ручная проверка смысла |
| `deploy/mas/overrides/consent.html` | 48 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/mas/overrides/index.html` | 38 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/mas/overrides/register_display_name.html` | 61 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/mas/overrides/register_password.html` | 96 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/mas/overrides/register_token_step.html` | 61 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/mas/purge-user.sh` | 76 | 4 | 0 | 0 | ручная проверка смысла |
| `deploy/matrix-invite/app.py` | 1542 | 8 | 2 | 60 | Python без docstring: 64, 71, 129, 152, 156, 176, 198, 208, 216, 221, 244, 254, 265, 295, 306, 319, 324, 386, 391, 396, 408, 452, 459, 557, 764, 778, 784, 800, 809, 816, 858, 877, 898, 907, 922, 932, 958, 985, 999, 1010, 1014, 1018, 1026, 1051, 1105, 1132, 1152, 1165, 1279, 1293, 1302, 1315, 1355, 1487, 1495, 1511, 1524, 1535, 1541 |
| `deploy/matrix-invite/matrix-invite.service` | 14 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/matrix-invite/msc4108.py` | 581 | 14 | 7 | 39 | Python без docstring: 33, 37, 44, 48, 53, 94, 102, 122, 146, 201, 209, 220, 235, 239, 244, 568, 579, 60, 76, 79, 84, 89, 168, 318, 341, 355, 370, 400, 404, 460, 525, 540, 554, 416 |
| `deploy/matrix-invite/sim_test_qr_login.py` | 227 | 10 | 1 | 3 | Python без docstring: 24, 28, 39 |
| `deploy/matrix/docker-compose.yml` | 69 | 17 | 0 | 0 | ручная проверка смысла |
| `deploy/matrix/element-config.json` | 36 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/matrix/homeserver.yaml` | 121 | 17 | 0 | 0 | ручная проверка смысла |
| `deploy/nginx/mspshield.conf` | 126 | 29 | 0 | 0 | ручная проверка смысла |
| `deploy/ntfy/docker-compose.yml` | 16 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/rtc/docker-compose.yml` | 46 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/rtc/element-call-config.json` | 13 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/rtc/livekit.yaml` | 15 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/vaultwarden/docker-compose.yml` | 24 | 4 | 0 | 0 | ручная проверка смысла |
| `deploy/wazuh-lab/apply_home_translation.py` | 44 | 1 | 1 | 0 | ручная проверка смысла |
| `deploy/wazuh-lab/apply_locale.py` | 49 | 3 | 1 | 0 | ручная проверка смысла |
| `deploy/wazuh-lab/generate_events.py` | 23 | 1 | 1 | 0 | ручная проверка смысла |
| `deploy/wazuh-lab/local_rules.xml` | 23 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/wazuh-lab/prepare.py` | 116 | 10 | 2 | 1 | ручная проверка смысла |
| `deploy/wazuh-lab/ru-RU.json` | 65 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/wazuh-lab/start.py` | 26 | 6 | 1 | 0 | ручная проверка смысла |
| `deploy/wazuh-lab/verify.py` | 41 | 2 | 1 | 1 | Python без docstring: 18 |
| `deploy/wazuh-lab/wazuh-home-ru.js` | 77 | 4 | 0 | 0 | ручная проверка смысла |
| `deploy/xmpp-invite/app.py` | 1026 | 4 | 1 | 46 | Python без docstring: 42, 49, 88, 96, 111, 115, 119, 125, 135, 141, 151, 174, 178, 195, 207, 257, 261, 270, 277, 287, 411, 451, 456, 469, 486, 515, 532, 539, 641, 649, 665, 679, 692, 711, 717, 727, 735, 748, 797, 809, 834, 846, 856, 866, 886, 901 |
| `deploy/xmpp-invite/xmpp-invite.service` | 15 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/xmpp/Dockerfile` | 50 | 13 | 0 | 0 | ручная проверка смысла |
| `deploy/xmpp/deploy.sh` | 132 | 13 | 0 | 0 | ручная проверка смысла |
| `deploy/xmpp/docker-compose.yml` | 40 | 10 | 0 | 0 | ручная проверка смысла |
| `deploy/xmpp/entrypoint.sh` | 23 | 9 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/Dockerfile.backend` | 18 | 2 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/cloud-init.yaml` | 199 | 57 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/deploy.ps1` | 582 | 74 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/docker-compose.yml` | 95 | 11 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/alertmanager/entrypoint.sh` | 22 | 4 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/backup-calendar.service` | 13 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/backup-calendar.timer` | 10 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/docker-compose.override.yml` | 24 | 2 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/docker-compose.yml` | 225 | 4 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/grafana/dashboards/msp-containers.json` | 257 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/grafana/dashboards/msp-services.json` | 290 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/grafana/dashboards/msp-vm.json` | 291 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/grafana/dashboards/mspshield-backups.json` | 308 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/grafana/dashboards/mspshield-overview.json` | 392 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/grafana/grafana.ini` | 94 | 25 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/grafana/provisioning/dashboards/dashboards.yml` | 22 | 6 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/grafana/provisioning/datasources/prometheus.yml` | 11 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/grafana/theme/mspshield.css` | 308 | 39 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/prometheus/blackbox.yml` | 54 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/prometheus/prometheus.yml` | 129 | 9 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/prometheus/rules/backups.yml` | 46 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/prometheus/rules/common.yml` | 46 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/prometheus/rules/containers.yml` | 44 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/prometheus/rules/services.yml` | 57 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/prometheus/rules/site.yml` | 46 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/prometheus/rules/ssl.yml` | 24 | 0 | 0 | 0 | нет комментариев/строк документации |
| `deploy/yandex/monitoring/restic-exporter/restic-metrics.sh` | 111 | 52 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/restic-exporter/run-backup.sh` | 65 | 25 | 0 | 0 | ручная проверка смысла |
| `deploy/yandex/monitoring/telegram-webhook/telegram_webhook.py` | 89 | 0 | 0 | 4 | нет комментариев/строк документации; Python без docstring: 15, 42, 64, 80 |
| `deploy/yandex/setup-on-vm.sh` | 297 | 58 | 0 | 0 | ручная проверка смысла |
| `docs/training/ansible/examples/inventory.yml` | 9 | 1 | 0 | 0 | ручная проверка смысла |
| `docs/training/ansible/examples/practice.yml` | 58 | 3 | 0 | 0 | ручная проверка смысла |
| `docs/vwautostart/install.ps1` | 69 | 0 | 0 | 0 | нет комментариев/строк документации |
| `docs/vwautostart/tray.ps1` | 118 | 0 | 0 | 0 | нет комментариев/строк документации |
| `docs/vwautostart/uninstall.ps1` | 21 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/components.json` | 21 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/craco.config.js` | 80 | 8 | 0 | 0 | ручная проверка смысла |
| `frontend/jsconfig.json` | 9 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/package.json` | 90 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/plugins/health-check/health-endpoints.js` | 213 | 38 | 0 | 0 | ручная проверка смысла |
| `frontend/plugins/health-check/webpack-health-plugin.js` | 120 | 9 | 0 | 0 | ручная проверка смысла |
| `frontend/postcss.config.js` | 6 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/public/docs/consent.html` | 10 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/public/docs/offer.html` | 17 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/public/docs/privacy.html` | 15 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/public/docs/sla.html` | 16 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/public/index.html` | 118 | 5 | 0 | 0 | ручная проверка смысла |
| `frontend/src/App.css` | 5 | 1 | 0 | 0 | ручная проверка смысла |
| `frontend/src/App.js` | 80 | 2 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/BackToTop.jsx` | 63 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/Footer.jsx` | 140 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/Nav.jsx` | 121 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/dashboards/BackupHealth.jsx` | 184 | 1 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/dashboards/DashboardWide.jsx` | 312 | 3 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/dashboards/GoldenSignals.jsx` | 195 | 3 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/dashboards/KpiTiles.jsx` | 75 | 1 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/dashboards/LatencyChart.jsx` | 181 | 2 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/dashboards/SlaTimeline.jsx` | 191 | 1 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/dashboards/TelegramAlert.jsx` | 225 | 2 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/dashboards/WazuhAlerts.jsx` | 226 | 2 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/dashboards/index.js` | 8 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/icons/OssIcon.jsx` | 76 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/icons/RuIcon.jsx` | 133 | 14 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/icons/ServiceIcon.jsx` | 159 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/icons/index.js` | 3 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/Alerts.jsx` | 156 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/Backups.jsx` | 58 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/CTAForm.jsx` | 590 | 9 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/sections/Capabilities.jsx` | 664 | 6 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/sections/Compliance.jsx` | 111 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/FAQ.jsx` | 82 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/FinalCta.jsx` | 135 | 2 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/sections/ForWhom.jsx` | 164 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/Hero.jsx` | 76 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/HowItWorks.jsx` | 153 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/Pain.jsx` | 328 | 2 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/sections/Pricing.jsx` | 214 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/Process.jsx` | 110 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/sections/Stack.jsx` | 201 | 2 | 0 | 0 | ручная проверка смысла |
| `frontend/src/components/sections/Visibility.jsx` | 83 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/accordion.jsx` | 41 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/alert-dialog.jsx` | 97 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/alert.jsx` | 47 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/aspect-ratio.jsx` | 5 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/avatar.jsx` | 33 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/badge.jsx` | 34 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/breadcrumb.jsx` | 92 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/button.jsx` | 48 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/calendar.jsx` | 71 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/card.jsx` | 50 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/carousel.jsx` | 193 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/checkbox.jsx` | 22 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/collapsible.jsx` | 9 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/command.jsx` | 116 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/context-menu.jsx` | 156 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/dialog.jsx` | 94 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/drawer.jsx` | 90 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/dropdown-menu.jsx` | 156 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/form.jsx` | 133 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/hover-card.jsx` | 23 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/input-otp.jsx` | 53 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/input.jsx` | 19 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/label.jsx` | 16 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/menubar.jsx` | 198 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/navigation-menu.jsx` | 104 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/pagination.jsx` | 100 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/popover.jsx` | 27 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/progress.jsx` | 21 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/radio-group.jsx` | 29 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/resizable.jsx` | 40 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/scroll-area.jsx` | 38 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/select.jsx` | 119 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/separator.jsx` | 23 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/sheet.jsx` | 108 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/skeleton.jsx` | 14 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/slider.jsx` | 21 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/sonner.jsx` | 28 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/switch.jsx` | 22 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/table.jsx` | 86 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/tabs.jsx` | 41 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/textarea.jsx` | 18 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/toast.jsx` | 85 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/toaster.jsx` | 33 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/toggle-group.jsx` | 43 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/toggle.jsx` | 40 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/components/ui/tooltip.jsx` | 26 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/content/landing.ru.json` | 267 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/content/useContent.js` | 88 | 29 | 0 | 0 | ручная проверка смысла |
| `frontend/src/hooks/use-toast.js` | 155 | 3 | 0 | 0 | ручная проверка смысла |
| `frontend/src/hooks/useReveal.js` | 27 | 4 | 0 | 0 | ручная проверка смысла |
| `frontend/src/index.css` | 461 | 20 | 0 | 0 | ручная проверка смысла |
| `frontend/src/index.js` | 11 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/lib/utils.js` | 6 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/pages/AdminLandingEdit.jsx` | 1149 | 21 | 0 | 0 | ручная проверка смысла |
| `frontend/src/pages/AdminLeads.jsx` | 541 | 4 | 0 | 0 | ручная проверка смысла |
| `frontend/src/pages/Landing.jsx` | 72 | 2 | 0 | 0 | ручная проверка смысла |
| `frontend/src/pages/NotFound.jsx` | 34 | 0 | 0 | 0 | нет комментариев/строк документации |
| `frontend/src/utils/metrika.js` | 10 | 3 | 0 | 0 | ручная проверка смысла |
| `frontend/tailwind.config.js` | 82 | 1 | 0 | 0 | ручная проверка смысла |
| `infra/terraform/cloud-init/bastion.yaml` | 34 | 5 | 0 | 0 | ручная проверка смысла |
| `infra/terraform/cloud-init/landing.yaml` | 45 | 10 | 0 | 0 | ручная проверка смысла |
| `infra/terraform/main.tf` | 253 | 48 | 0 | 0 | ручная проверка смысла |
| `infra/terraform/variables.tf` | 39 | 6 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-awg-add-admin-peer.sh` | 35 | 4 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-awg-install.sh` | 23 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-backup-setup.sh` | 97 | 25 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-backup-verify2.sh` | 58 | 1 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-bootstrap.sh` | 83 | 4 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-coturn-fix.sh` | 19 | 1 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-coturn.sh` | 80 | 5 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-create-postmaster.sh` | 51 | 5 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-docker-dns-fix.sh` | 38 | 9 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-fix-iface-name.sh` | 110 | 16 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-fix-route-swap.sh` | 64 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-fix-routing.sh` | 39 | 9 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-free-disk.sh` | 34 | 3 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-mail-cert.sh` | 50 | 10 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-mail-yandex-test.sh` | 33 | 1 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-msg-dns-check.sh` | 20 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-postdeploy.sh` | 40 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-postreboot-check.sh` | 26 | 1 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-secrets-export.sh` | 145 | 17 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-secrets-inventory.sh` | 20 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-ssh-lockdown-ufw.sh` | 25 | 9 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-stalwart-logs.sh` | 17 | 8 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-test-smtp.sh` | 42 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-xmpp-connect-diag.sh` | 31 | 3 | 0 | 0 | ручная проверка смысла |
| `migration/cloudru-xmpp-test-accounts.sh` | 36 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/diag.sh` | 25 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/migrate.ps1` | 42 | 2 | 0 | 0 | ручная проверка смысла |
| `migration/prometheus-targets.sh` | 20 | 1 | 0 | 0 | ручная проверка смысла |
| `migration/restic-backup.sh` | 120 | 16 | 0 | 0 | ручная проверка смысла |
| `migration/restore-on-vm.sh` | 126 | 20 | 0 | 0 | ручная проверка смысла |
| `scripts/audit_junior_readability.py` | 84 | 2 | 3 | 2 | ручная проверка смысла |
| `scripts/backup_calendar.py` | 93 | 2 | 5 | 4 | ручная проверка смысла |
| `scripts/deployment/integrate_backup_calendar.py` | 33 | 1 | 1 | 0 | ручная проверка смысла |
| `scripts/deployment/preflight.sh` | 84 | 10 | 0 | 0 | ручная проверка смысла |
| `scripts/deployment/publish_landing.py` | 60 | 2 | 1 | 1 | Python без docstring: 17 |
| `scripts/deployment/verify_calendar.py` | 32 | 1 | 1 | 1 | Python без docstring: 10 |
| `scripts/kaiten_bootstrap.py` | 220 | 2 | 2 | 8 | Python без docstring: 49, 56, 89, 109, 133, 145, 178 |
| `scripts/max_setup_webhook.py` | 170 | 1 | 1 | 6 | Python без docstring: 41, 49, 55, 68, 78, 101 |
| `scripts/pre_audit.py` | 748 | 45 | 11 | 15 | Python без docstring: 107, 111, 117, 675, 406 |
| `scripts/production-readiness/external_scan.sh` | 34 | 8 | 0 | 0 | ручная проверка смысла |
| `scripts/seed_test_lead.py` | 91 | 1 | 1 | 1 | Python без docstring: 60 |
| `scripts/tests/test_backup_calendar.py` | 28 | 0 | 0 | 2 | нет комментариев/строк документации; Python без docstring: 10, 21 |
| `scripts/tunnel-monitoring.ps1` | 34 | 2 | 0 | 0 | ручная проверка смысла |
| `scripts/validate_business_consistency.py` | 63 | 3 | 1 | 1 | Python без docstring: 48 |
| `scripts/validate_deployment_freshness.py` | 18 | 1 | 0 | 3 | Python без docstring: 5, 6, 8 |
| `scripts/validate_markdown_links.py` | 63 | 1 | 1 | 0 | ручная проверка смысла |
| `scripts/validate_max_consistency.py` | 51 | 1 | 1 | 3 | Python без docstring: 14, 17, 21 |
| `scripts/validate_operational_consistency.py` | 41 | 2 | 1 | 3 | Python без docstring: 9, 10, 12 |
| `services/matrix_alerter/Dockerfile` | 14 | 1 | 0 | 0 | ручная проверка смысла |
| `services/matrix_alerter/__init__.py` | 1 | 0 | 1 | 0 | ручная проверка смысла |
| `services/matrix_alerter/alerter.py` | 179 | 2 | 9 | 8 | ручная проверка смысла |
| `services/max_alerter/Dockerfile` | 16 | 2 | 0 | 0 | ручная проверка смысла |
| `services/max_alerter/__init__.py` | 3 | 0 | 1 | 0 | ручная проверка смысла |
| `services/max_alerter/auth.py` | 121 | 1 | 4 | 7 | Python без docstring: 99, 31, 34, 41, 44, 90 |
| `services/max_alerter/sender.py` | 154 | 2 | 8 | 8 | Python без docstring: 63 |
| `services/max_alerter/test_sender.py` | 47 | 0 | 1 | 11 | Python без docstring: 8, 20, 35, 22, 23, 24, 38, 40, 41, 42, 43 |
| `services/max_alerter/webhook.py` | 94 | 0 | 2 | 6 | Python без docstring: 38, 45, 68, 78, 91 |
| `services/vm_watcher/config.example.json` | 8 | 0 | 0 | 0 | нет комментариев/строк документации |
| `services/vm_watcher/install.ps1` | 32 | 2 | 0 | 0 | ручная проверка смысла |
| `services/vm_watcher/tray.ps1` | 118 | 0 | 0 | 0 | нет комментариев/строк документации |
| `services/vm_watcher/uninstall.ps1` | 19 | 1 | 0 | 0 | ручная проверка смысла |
| `services/vm_watcher/watcher.ps1` | 70 | 3 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/amneziawg/awg-client-template.conf` | 67 | 45 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/amneziawg/awg-server-template.conf` | 82 | 62 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/amneziawg/awg_bootstrap.sh` | 102 | 30 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/amneziawg/tenant_add.sh` | 139 | 34 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/ansible.cfg` | 34 | 21 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/group_vars/landing/vault.example.yml` | 56 | 24 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/group_vars/tenants/vault.example.yml` | 15 | 9 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/inventory/prod.yml` | 46 | 27 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/playbooks/backup_install.yml` | 73 | 18 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/playbooks/patch_disruptive.yml` | 50 | 19 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/playbooks/patch_nondisruptive.yml` | 37 | 14 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/playbooks/site.yml` | 66 | 24 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/ad_health_check/defaults/main.yml` | 5 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/ad_health_check/tasks/main.yml` | 59 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/ad_health_check/templates/ad_health_check.sh.j2` | 36 | 9 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/alertmanager/defaults/main.yml` | 16 | 4 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/alertmanager/handlers/main.yml` | 5 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/alertmanager/tasks/main.yml` | 60 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/alertmanager/templates/alertmanager.yml.j2` | 99 | 10 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/awg_hub/defaults/main.yml` | 47 | 26 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/awg_hub/handlers/main.yml` | 5 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/awg_hub/tasks/main.yml` | 58 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/awg_hub/templates/awg0.conf.j2` | 28 | 4 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/base_hardening/defaults/main.yml` | 15 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/base_hardening/handlers/main.yml` | 5 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/base_hardening/tasks/main.yml` | 43 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/baseline/defaults/main.yml` | 19 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/baseline/handlers/main.yml` | 15 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/baseline/tasks/main.yml` | 79 | 4 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/fastapi_backend/defaults/main.yml` | 7 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/fastapi_backend/handlers/main.yml` | 6 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/fastapi_backend/tasks/main.yml` | 80 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/fastapi_backend/templates/mspshield-backend.service.j2` | 21 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/mongo/defaults/main.yml` | 5 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/mongo/handlers/main.yml` | 5 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/mongo/tasks/main.yml` | 65 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/monitoring_agent/defaults/main.yml` | 6 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/monitoring_agent/handlers/main.yml` | 6 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/monitoring_agent/tasks/main.yml` | 77 | 5 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/monitoring_agent/templates/promtail.yml.j2` | 36 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/nginx/defaults/main.yml` | 6 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/nginx/handlers/main.yml` | 5 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/ansible/roles/nginx/tasks/main.yml` | 100 | 14 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/nginx/templates/mspshield.conf.j2` | 63 | 2 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/restic_client/defaults/main.yml` | 20 | 7 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/restic_client/tasks/main.yml` | 104 | 5 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/ansible/roles/restic_client/templates/mspshield-backup.sh.j2` | 33 | 6 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/docker/docker-compose.yml` | 264 | 43 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/grafana/loki-config.yml` | 124 | 20 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/monitoring/alertmanager.yml` | 143 | 47 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/monitoring/prometheus.yml` | 70 | 26 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/monitoring/rules/ad.yml` | 18 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/monitoring/rules/backups.yml` | 18 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/monitoring/rules/common.yml` | 34 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/monitoring/rules/ssl.yml` | 18 | 0 | 0 | 0 | нет комментариев/строк документации |
| `technical/0_Common/prometheus/blackbox.yml` | 80 | 14 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/scripts/dr_drill.sh` | 61 | 12 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/scripts/monthly_report.py` | 193 | 10 | 1 | 5 | Python без docstring: 85, 96, 108, 120, 124 |
| `technical/0_Common/scripts/rotate_junior_access.sh` | 75 | 31 | 0 | 0 | ручная проверка смысла |
| `technical/0_Common/scripts/verify_all.sh` | 210 | 29 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/CLIENT/amneziawg/setup_awg_client.sh` | 220 | 35 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/CLIENT/node_exporter/install_linux.sh` | 124 | 17 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/CLIENT/restic_backup/install_restic_linux.sh` | 372 | 68 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/CLIENT/restic_backup/restic_backup.sh` | 215 | 41 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/CLIENT/windows_exporter/install_windows.ps1` | 175 | 40 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/EXECUTOR/alertmanager/alertmanager.yml` | 173 | 40 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/EXECUTOR/amneziawg/setup_awg_bastion.sh` | 235 | 59 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/EXECUTOR/grafana/provisioning/dashboards/dashboards.yml` | 32 | 4 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/EXECUTOR/grafana/provisioning/datasources/datasources.yml` | 46 | 9 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/EXECUTOR/prometheus/prometheus.yml` | 192 | 114 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/EXECUTOR/prometheus/rules/bronze_alerts.yml` | 492 | 52 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/EXECUTOR/scripts/onboard_client.sh` | 381 | 70 | 0 | 0 | ручная проверка смысла |
| `technical/1_Bronze/EXECUTOR/scripts/weekly_report.sh` | 287 | 32 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/CLIENT/ad_management/gpo_baseline.ps1` | 118 | 37 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/CLIENT/promtail/install_promtail.sh` | 222 | 81 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/CLIENT/promtail/promtail-config.yml` | 87 | 44 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/CLIENT/puppet_agent/install_puppet_agent.sh` | 109 | 40 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/CLIENT/puppet_agent/install_puppet_agent_windows.ps1` | 68 | 24 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/ansible/playbooks/deploy_bronze.yml` | 443 | 22 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/ansible/playbooks/deploy_gold.yml` | 264 | 16 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/ansible/playbooks/deploy_silver.yml` | 309 | 12 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/ansible/roles/inventory_template/vars.yml` | 80 | 34 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/ansible/roles/node_exporter_tasks.yml` | 114 | 3 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/puppet/modules/base_linux/init.pp` | 204 | 43 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/puppet/modules/hardening/init.pp` | 203 | 52 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/puppet/modules/monitoring_agents/init.pp` | 138 | 38 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/puppet/site.pp` | 98 | 68 | 0 | 0 | ручная проверка смысла |
| `technical/2_Silver/EXECUTOR/silver_alerts.yml` | 191 | 22 | 0 | 0 | ручная проверка смысла |
| `technical/3_Gold/CLIENT/kaspersky/kes_deploy_gpo.ps1` | 67 | 30 | 0 | 0 | ручная проверка смысла |
| `technical/3_Gold/CLIENT/kaspersky/monitor_kes.ps1` | 66 | 35 | 0 | 0 | ручная проверка смысла |
| `technical/3_Gold/CLIENT/wazuh_agent/install_wazuh_agent_linux.sh` | 171 | 26 | 0 | 0 | ручная проверка смысла |
| `technical/3_Gold/CLIENT/wazuh_agent/install_wazuh_agent_windows.ps1` | 225 | 34 | 0 | 0 | ручная проверка смысла |
| `technical/3_Gold/EXECUTOR/gold_alerts.yml` | 215 | 27 | 0 | 0 | ручная проверка смысла |
| `technical/3_Gold/EXECUTOR/osticket/docker-compose.yml` | 95 | 14 | 0 | 0 | ручная проверка смысла |
| `technical/3_Gold/EXECUTOR/wazuh/wazuh_manager_ossec.conf` | 219 | 21 | 0 | 0 | ручная проверка смысла |
