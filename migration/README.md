# Миграция MSPShield на новую VM

## Принципы

- переносим данные и отдельно проверенные session artifacts, а не старые `.env`;
- SSH host key сверяем через console/provider metadata; `StrictHostKeyChecking=no` запрещён;
- DNS переключаем только после health, alert и restore gates;
- snapshot не заменяет clean-room restore.

## Артефакты

| Файл | Источник | Восстановление |
|---|---|---|
| `mongodump.archive.gz` | логический dump Mongo | `mongorestore --drop` |
| `vaultwarden-data.tar.gz` | остановленный writer volume | Docker volume |
| `stalwart-etc.tar.gz` | mail config/domain/DKIM | Docker volume |
| `stalwart-data.tar.gz` | mail data | Docker volume |
| `max-session.tar.gz` | остановленный max-alerter | bind directory |

Архивы создаёт `migration/restic-backup.sh`. Raw live-copy `/var/lib/docker/volumes` не используется.

## Новая VM

1. Deploy кода.
2. Создать новые `backend/.env`, `deploy/yandex/.env`, `monitoring/.env`.
3. `bash scripts/deployment/preflight.sh --fix`.
4. Загрузить только перечисленные артефакты в `/tmp/migration`.
5. Запустить:

```bash
sudo /tmp/migration/restore-on-vm.sh
```

## Gate DNS switch

- [ ] backend, Prometheus, Alertmanager и MAX health зелёные;
- [ ] Mongo count и выборочные записи проверены;
- [ ] Vaultwarden login проверен;
- [ ] Stalwart домен/ящик/DKIM проверены, если mail profile включён;
- [ ] `max_alerter.auth` возвращает 0 без `--authorize`;
- [ ] P1 доставлен в MAX и Postbox email;
- [ ] новый restic snapshot создан;
- [ ] файл восстановлен в clean target, RTO/RPO записаны;
- [ ] внешний scan не показывает internal ports.

Если MAX session не принимается, только оператор выполняет:

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

Старую VM держать выключенной до завершения периода наблюдения; удалять после подтверждённого backup новой среды.
