# 36. Onboarding, steady сохранённые данные и завершение обслуживания

> **Учебная ситуация.** Подписанный клиент ещё не должен автоматически попадать под SLA.

## Главное

Pre-onboarding проверяет оплату, документы, contacts и доступность inputs. Technical onboarding создаёт inventory, access, baseline, monitoring и резервная копия.

Acceptance переводит систему в steady сохранённые данные только после оговорённых checks. Unknown technical debt фиксируется, а не молча принимается.

Offboarding возвращает данные, отзывает accounts и фиксирует deletion/retention. владелец проекта клиента сохраняет recovery control.

## Слова, которые встретятся дальше

### acceptance

Формальное подтверждение, что onboarding outputs соответствуют критериям и начинается steady-сохранённые данные responsibility.

### завершение обслуживания

Управляемая передача данных/документации и отзыв доступов при завершении услуги.

### secret lifecycle

Создание, хранение, выдача, использование, rotation, revocation и уничтожение секрет доступа. Пропуск завершение обслуживания оставляет orphan access.

## Как это работает

После Won sales передаёт не обещания в чате, а подписанный границы услуги и contacts. Onboarding создаёт baseline и список open risks. Acceptance отделяет внедрение от recurring service. Offboarding зеркально удаляет доступ, передаёт artifacts и учитывает retention резервная копияs.

## Пример

```text
Won → pre-onboarding gate → technical onboarding
→ acceptance → operation/review → renewal или завершение обслуживания
```

### Что здесь происходит

- `Won → pre-onboarding gate → technical onboarding` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `→ acceptance → operation/review → renewal или завершение обслуживания` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Проведите mock-client через lifecycle.
2. Создайте access matrix и baseline.
3. Выполните завершение обслуживания и найдите orphan access.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| SLA начался до acceptance | риск ложного breach. |
| Секреты в Kaiten | перенести в Vaultwarden и ротировать. |


## Проверьте себя

1. Объясните `acceptance` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `завершение обслуживания` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `secret lifecycle` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «SLA начался до acceptance» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/operations/CLIENT_LIFECYCLE.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/operations/CLIENT_LIFECYCLE.md)
- [docs/onboarding/README.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/onboarding/README.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

