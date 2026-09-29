# 22. Backup, restore, RPO и RTO

> **Учебная ситуация.** Backup job зелёный, но никто не знает, можно ли восстановить сервис.

Предыдущая глава: [глава 21](./21-alerting-и-доставка-в-max.md).

## Модель, которую нужно построить

Backup — копия определённого набора данных; snapshot — зафиксированное состояние repository. Ни одно слово не означает автоматически consistency.

RPO измеряет допустимую потерю по времени, RTO — время восстановления сервиса. Цель становится доказанной только в упражнении.

MSPShield требует Mongo dump, Vaultwarden data, оба Stalwart volumes и MAX session. Ключи repository и restore credentials — отдельная зависимость.

## Термины в рабочем смысле

### backup set

Явный перечень данных, конфигураций и ключей, необходимых для восстановления услуги. Неизвестный объект не попадает в backup автоматически.

### RPO

Максимальная приемлемая потеря данных, выраженная временем между последней восстановимой точкой и инцидентом.

### RTO

Измеренное или целевое время от начала восстановления до принятого service state.

## Что происходит внутри

Capture выбирает согласованную точку Mongo и stateful services, restic сохраняет encrypted snapshot, `restic check` проверяет repository structure, restore materializes files. Затем приложение должно стартовать и пройти acceptance. Только последняя часть доказывает recoverability.

## Разобранный пример

```bash
sudo bash /opt/restic-scripts/backup.sh
source /etc/restic/env.sh
restic snapshots --latest 1
restic check
restic restore latest --target /tmp/restore-test
```

### Как читать пример

- `sudo bash /opt/restic-scripts/backup.sh` — `sudo` запускает следующую программу с повышенной effective identity; shell уже обработал кавычки, glob и redirection.
- `source /etc/restic/env.sh` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `restic snapshots --latest 1` — Restic-команда работает с repository из environment; `snapshots/check/restore` отвечают на разные вопросы и не взаимозаменяемы.
- `restic check` — Restic-команда работает с repository из environment; `snapshots/check/restore` отвечают на разные вопросы и не взаимозаменяемы.
- `restic restore latest --target /tmp/restore-test` — Restic-команда работает с repository из environment; `snapshots/check/restore` отвечают на разные вопросы и не взаимозаменяемы.

## Практикум

1. Сделайте snapshot.
2. Восстановите в clean target, не поверх production.
3. Поднимите сервис и измерьте RPO/RTO.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Snapshot есть, размер 0 | Это сужает область поиска, но не доказывает единственную причину | capture path неверен. |
| Repository доступен, password потерян | Это сужает область поиска, но не доказывает единственную причину | restore невозможен. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Backup job зелёный, но никто не знает, можно ли восстановить сервис.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `backup set` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `RPO` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `RTO` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Snapshot есть, размер 0» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [migration/restic-backup.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/migration/restic-backup.sh)
- [docs/deployment/disaster_recovery.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/disaster_recovery.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

## Условие перехода

Глава завершена, если вы можете связно объяснить `backup set`, `RPO`, `RTO`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
