# 11. MongoDB, persistence и consistency

> **Учебная ситуация.** После recreate backend заявки остаются, а после неправильного удаления volume исчезают.

Предыдущая глава: [глава 10](./10-python-путь-запроса-от-socket-до-функции.md).

## Модель, которую нужно построить

Mongo хранит BSON documents в collection. `_id` уникален; прикладной `id` требует собственного unique index, если по нему предотвращаются дубли.

Container writable layer связан с конкретным container. Named volume имеет отдельный lifecycle и монтируется в `/data/db`.

Dump — логическое представление базы; tar volume — файловое. Для работающей БД без coordination файловая копия может быть несогласованной.

## Термины в рабочем смысле

### document

BSON-объект MongoDB с полями и `_id`. Свободная структура не отменяет необходимость прикладной валидации и indexes.

### index-db

Структура, ускоряющая поиск и способная обеспечивать uniqueness. Она увеличивает стоимость записи и занимает storage.

### volume

Storage с lifecycle отдельно от container. Backup volume всё равно должен учитывать consistency приложения.

## Что происходит внутри

Mongo ACK подтверждает запись согласно write concern, но не доставку в Kaiten. Volume сохраняет database files между containers; dump создаёт переносимый logical stream. Restore в другую database позволяет проверить структуру и counts без разрушения production.

## Разобранный пример

```bash
docker exec msp-mongo-1 mongosh mspshield --eval 'db.leads.countDocuments()'
mongodump --uri mongodb://127.0.0.1:27017/mspshield --archive=lead.gz --gzip
mongorestore --uri mongodb://127.0.0.1:27017/test --archive=lead.gz --gzip
```

### Как читать пример

- `docker exec msp-mongo-1 mongosh mspshield --eval 'db.leads.countDocuments()'` — `docker exec` создаёт новый process в namespaces работающего container; это не новый container и не проверка restart path.
- `mongodump --uri mongodb://127.0.0.1:27017/mspshield --archive=lead.gz --gzip` — `mongodump` создаёт logical BSON dump; `--archive --gzip` формирует один сжатый stream.
- `mongorestore --uri mongodb://127.0.0.1:27017/test --archive=lead.gz --gzip` — `mongorestore` записывает данные в target; `--drop` удаляет существующие collections и требует отдельного подтверждения.

## Практикум

1. Создайте несколько documents.
2. Сделайте dump и restore в другую database.
3. Пересоздайте container с тем же volume и без него.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Повтор формы создаёт две записи | Это сужает область поиска, но не доказывает единственную причину | нет idempotency/unique constraint. |
| Dump есть, restore не проверен | Это сужает область поиска, но не доказывает единственную причину | recoverability неизвестна. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **После recreate backend заявки остаются, а после неправильного удаления volume исчезают.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `document` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `index-db` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `volume` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Повтор формы создаёт две записи» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [deploy/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/deploy/yandex/docker-compose.yml)
- [migration/restic-backup.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/migration/restic-backup.sh)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

## Условие перехода

Глава завершена, если вы можете связно объяснить `document`, `index-db`, `volume`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
