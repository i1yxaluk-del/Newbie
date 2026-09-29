# 11. MongoDB, persistence и consistency

> **Учебная ситуация.** После recreate backend заявки остаются, а после неправильного удаления volume исчезают.

## Главное

Mongo хранит BSON documents в collection. `_id` уникален; прикладной `id` требует собственного unique index, если по нему предотвращаются дубли.

Container writable layer связан с конкретным container. Named volume имеет отдельный lifecycle и монтируется в `/data/db`.

Dump — логическое представление базы; tar volume — файловое. Для работающей БД без coordination файловая копия может быть несогласованной.

## Слова, которые встретятся дальше

### document

BSON-объект MongoDB с полями и `_id`. Свободная структура не отменяет необходимость прикладной валидации и indexes.

### index-db

Структура, ускоряющая поиск и способная обеспечивать uniqueness. Она увеличивает стоимость записи и занимает storage.

### volume

Storage с lifecycle отдельно от container. Резервная копия volume всё равно должен учитывать consistency приложения.

## Как это работает

Mongo ACK подтверждает запись согласно write concern, но не доставку в Kaiten. Volume сохраняет database files между containers; dump создаёт переносимый logical stream. Restore в другую database позволяет проверить структуру и counts без разрушения production.

## Пример

```bash
docker exec msp-mongo-1 mongosh mspshield --eval 'db.leads.countDocuments()'
mongodump --uri mongodb://127.0.0.1:27017/mspshield --archive=lead.gz --gzip
mongoвосстановление --uri mongodb://127.0.0.1:27017/test --archive=lead.gz --gzip
```

### Что здесь происходит

- `docker exec msp-mongo-1 mongosh mspshield --eval 'db.leads.countDocuments()'` — `docker exec` создаёт новый процесс в namespaces работающего container; это не новый container и не проверка restart path.
- `mongodump --uri mongodb://127.0.0.1:27017/mspshield --archive=lead.gz --gzip` — `mongodump` создаёт logical BSON dump; `--archive --gzip` формирует один сжатый stream.
- `mongoвосстановление --uri mongodb://127.0.0.1:27017/test --archive=lead.gz --gzip` — `mongoвосстановление` записывает данные в target; `--drop` удаляет существующие collections и требует отдельного подтверждения.

## Практикум

1. Создайте несколько documents.
2. Сделайте dump и восстановление в другую database.
3. Пересоздайте container с тем же volume и без него.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Повтор формы создаёт две записи | нет idempotency/unique constraint. |
| Dump есть, восстановление не проверен | recoverability неизвестна. |


## Проверьте себя

1. Объясните `document` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `index-db` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `volume` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Повтор формы создаёт две записи» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [развёртывание/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/docker-compose.yml)
- [migration/restic-резервная копия.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/migration/restic-резервная копия.sh)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

