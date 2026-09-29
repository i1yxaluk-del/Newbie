# 23. Миграция и Disaster Recovery

> **Учебная ситуация.** Нужно перенести проект в новый аккаунт без потери данных и с возможностью отката.

## Главное

Migration — плановое перемещение; DR — восстановление после серьёзного отказа. Шаги похожи, но доступность исходной системы и допустимый риск различаются.

Cutover меняет направление production traffic. До него новая среда проверяется по IP/hosts override; после — действует observation window.

Restore script обязан fail closed при пустом томе. Для Stalwart восстанавливаются etc и data; иначе bootstrap выглядит как «сервис запущен», но конфигурации нет.

## Как это работает

До cutover сравниваются counts, volume sizes, учётные записи, queue, health и предупреждение delivery. DNS меняет только имя→IP, но не переносит данные. Observation window сохраняет старую VM доступной для rollback; её нельзя удалять сразу после первого 200.

## Пример

```bash
sudo bash -c 'source /etc/restic/env.sh && restic восстановление latest --target /tmp/восстановление'
sudo MIGRATION_DIR=/tmp/migration bash migration/восстановление-on-vm.sh
docker logs msp-stalwart-1 | grep -c 'bootstrap mode'
```

## Практикум

1. Составьте список систем до переноса.
2. Перенесите на clean VM и проверьте data counts/volume sizes.
3. Отрепетируйте DNS cutover и rollback.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| ICMP ok, TCP timeout | сменить IP до DNS. |
| Новый bucket даёт SignatureDoesNotMatch | секрет доступаs связаны с аккаунтом. |

## Источники проекта

- [docs/развёртываниеment/MIGRATION_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/MIGRATION_RUNBOOK.md)
- [migration/восстановление-on-vm.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/migration/восстановление-on-vm.sh)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

