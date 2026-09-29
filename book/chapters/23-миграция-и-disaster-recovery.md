# 23. Миграция и Disaster Recovery

> **Учебная ситуация.** Нужно перенести проект в новый аккаунт без потери данных и с возможностью отката.

Предыдущая глава: [глава 22](./22-backup-restore-rpo-и-rto.md).

## Модель, которую нужно построить

Migration — плановое перемещение; DR — восстановление после серьёзного отказа. Шаги похожи, но доступность исходной системы и допустимый риск различаются.

Cutover меняет направление production traffic. До него новая среда проверяется по IP/hosts override; после — действует observation window.

Restore script обязан fail closed при пустом томе. Для Stalwart восстанавливаются etc и data; иначе bootstrap выглядит как «сервис запущен», но конфигурации нет.

## Термины в рабочем смысле

### migration

Плановое перемещение системы с доступным источником и controlled cutover. Отличается от DR доступностью исходного состояния.

### cutover

Момент перевода production traffic или authority на новую среду. Требует критериев go/no-go и rollback.

### bootstrap mode

Начальное состояние Stalwart без восстановленной рабочей конфигурации. Process может быть healthy, но service для клиента фактически потерян.

## Что происходит внутри

До cutover сравниваются counts, volume sizes, accounts, queue, health и alert delivery. DNS меняет только имя→IP, но не переносит данные. Observation window сохраняет старую VM доступной для rollback; её нельзя удалять сразу после первого 200.

## Разобранный пример

```bash
sudo bash -c 'source /etc/restic/env.sh && restic restore latest --target /tmp/restore'
sudo MIGRATION_DIR=/tmp/migration bash migration/restore-on-vm.sh
docker logs msp-stalwart-1 | grep -c 'bootstrap mode'
```

### Как читать пример

- `sudo bash -c 'source /etc/restic/env.sh && restic restore latest --target /tmp/restore'` — `sudo` запускает следующую программу с повышенной effective identity; shell уже обработал кавычки, glob и redirection.
- `sudo MIGRATION_DIR=/tmp/migration bash migration/restore-on-vm.sh` — `sudo` запускает следующую программу с повышенной effective identity; shell уже обработал кавычки, glob и redirection.
- `docker logs msp-stalwart-1 | grep -c 'bootstrap mode'` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Составьте inventory до переноса.
2. Перенесите на clean VM и проверьте data counts/volume sizes.
3. Отрепетируйте DNS cutover и rollback.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| ICMP ok, TCP timeout | Это сужает область поиска, но не доказывает единственную причину | сменить IP до DNS. |
| Новый bucket даёт SignatureDoesNotMatch | Это сужает область поиска, но не доказывает единственную причину | credentials связаны с аккаунтом. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Нужно перенести проект в новый аккаунт без потери данных и с возможностью отката.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `migration` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `cutover` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `bootstrap mode` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «ICMP ok, TCP timeout» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/deployment/MIGRATION_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/MIGRATION_RUNBOOK.md)
- [migration/restore-on-vm.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/migration/restore-on-vm.sh)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

## Условие перехода

Глава завершена, если вы можете связно объяснить `migration`, `cutover`, `bootstrap mode`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
