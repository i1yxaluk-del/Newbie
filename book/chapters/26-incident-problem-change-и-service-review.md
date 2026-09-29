# 26. Incident, problem, change и service review

> **Учебная ситуация.** Нужно восстановить сайт и не превратить расследование в хаотичные команды.

## Главное

Incident управляет текущим impact; problem ищет повторяемую причину; change изменяет controlled сохранённые данные. Один ticket может породить все три записи.

Mitigation уменьшает impact, root cause объясняет механизм. Перезапуск может быть mitigation, но не доказательством причины.

Timeline строится по timestamped подтверждение. Postmortem отделяет contributing conditions от персонального обвинения.

## Слова, которые встретятся дальше

### incident

Незапланированный impact или существенная деградация, требующая восстановления услуги сейчас.

### problem

Причина или класс причин одного или нескольких incidents; работа problem management может продолжаться после восстановления.

### change

Контролируемое изменение состояния с владелец, окном, test и rollback. Сам факт срочности не отменяет запись результата.

## Как это работает

Incident lead управляет приоритетом и коммуникацией, technical responder меняет систему, scribe ведёт timeline. После recovery problem analysis проверяет гипотезы подтверждение. Preventive action должна менять code/config/процесс и иметь test, иначе это пожелание.

## Пример

```text
14:02 предупреждение: external probe failed
14:05 владелец acknowledged P1
14:09 direct backend health=200, Caddy=503
14:14 replaced provisioning Caddyfile
14:17 external HTTPS=200
```

### Что здесь происходит

- `14:02 предупреждение: external probe failed` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `14:05 владелец acknowledged P1` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `14:09 direct backend health=200, Caddy=503` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `14:14 replaced provisioning Caddyfile` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `14:17 external HTTPS=200` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Проведите tabletop Caddy 503.
2. Назначьте incident lead и communications.
3. Сформулируйте preventive action с владелец/date/test.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Много людей меняют систему | остановить некоординированные changes. |
| Нет исходного состояния | фиксировать текущие факты, не реконструировать уверенно. |


## Проверьте себя

1. Объясните `incident` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `problem` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `change` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Много людей меняют систему» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/runbooks/README.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/runbooks/README.md)
- [docs/post_mortem_template.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/post_mortem_template.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

