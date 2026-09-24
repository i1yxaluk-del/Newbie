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

## Evidence каждого lab

- дата, стенд и версия commit;
- команды без секретов;
- ожидаемый и фактический результат;
- screenshot/log fragment;
- rollback и его результат;
- вывод наставника: pass/repeat.

Доступ L2 выдаётся только после Labs 1–6 и общего Bronze-сценария.
