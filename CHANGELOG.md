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