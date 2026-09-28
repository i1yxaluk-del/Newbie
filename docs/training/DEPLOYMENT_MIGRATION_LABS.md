# Практикум Junior: deployment, backup и migration

Все упражнения выполняются на стенде без production-секретов и ПДн.

| Lab | Сценарий | Успех | Критический провал |
|---|---|---|---|
| 1 | `.env` с BOM/CRLF и пустым ADMIN_TOKEN | preflight находит обе проблемы, Junior объясняет риск | просто удаляет файл или печатает секреты |
| 2 | Alertmanager с отсутствующим SMTP password | Compose/entrypoint fail-fast, после фикса тестовое письмо доставлено | отключает auth/TLS |
| 3 | backup Mongo + Vaultwarden + Stalwart | создаёт staging archives и восстанавливает в clean VM | копирует live Mongo volume |
| 4 | перенос MAX session | session check проходит без `--authorize` | запускает SMS автоматически |
| 5 | VM watcher при закрытом ICMP | TCP/443 различает stopped и network failure | использует только ping или hardcoded VM ID |
| 6 | смена SSH host key | сверяет fingerprint в console и обновляет known_hosts | `StrictHostKeyChecking=no` |
| 7 | полный tenant onboarding | scope → change → alert → restore → report | начинает без договора/окна/rollback |
| 8 | Миграция на чистую ВМ по `MIGRATION_RUNBOOK` §9 (симуляция) | тома восстановлены (du ≈ бэкап), Stalwart не в bootstrap, сайт 200 | молчаливые пустые тома; bootstrap-режим; Caddy-заглушка |

## Evidence каждого lab

- дата, стенд и версия commit;
- команды без секретов;
- ожидаемый и фактический результат;
- screenshot/log fragment;
- rollback и его результат;
- вывод наставника: pass/repeat.

## Разбор кейсов миграции 28.09 (перед Lab 8)

Прочитать [`../deployment/MIGRATION_RUNBOOK.md`](../deployment/MIGRATION_RUNBOOK.md) §9 и разобрать с Junior'ом:

1. Почему «сайт не работает» не всегда вина сайта? (доступность IP из сети/региона, §9.2)
2. Чем опасен `sudo cp root-only/*.tar.gz`? (glob раскрывается до sudo, §9.4)
3. Почему Stalwart без томов уходит в bootstrap и что это значит для почты? (§9.4)
4. Что пересоздаётся при переезде в новый аккаунт? (ключ+DKIM Postbox, ключ+init restic, §9.5–9.6)
5. Какие два gate добавились перед DNS switch? (TCP из региона; отсутствие bootstrap, §9.8)

Эталонные формулировки — в §9.2–§9.8.

Доступ L2 выдаётся только после Labs 1–6 и общего Bronze-сценария.
