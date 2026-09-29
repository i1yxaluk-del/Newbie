# 36. Onboarding, steady state и offboarding

> **Учебная ситуация.** Подписанный клиент ещё не должен автоматически попадать под SLA.

Предыдущая глава: [глава 35](./35-договор-sla-периметр-и-пдн.md).

## Модель, которую нужно построить

Pre-onboarding проверяет оплату, документы, contacts и доступность inputs. Technical onboarding создаёт inventory, access, baseline, monitoring и backup.

Acceptance переводит систему в steady state только после оговорённых checks. Unknown technical debt фиксируется, а не молча принимается.

Offboarding возвращает данные, отзывает accounts и фиксирует deletion/retention. Owner клиента сохраняет recovery control.

## Термины в рабочем смысле

### acceptance

Формальное подтверждение, что onboarding outputs соответствуют критериям и начинается steady-state responsibility.

### offboarding

Управляемая передача данных/документации и отзыв доступов при завершении услуги.

### secret lifecycle

Создание, хранение, выдача, использование, rotation, revocation и уничтожение credential. Пропуск offboarding оставляет orphan access.

## Что происходит внутри

После Won sales передаёт не обещания в чате, а подписанный scope и contacts. Onboarding создаёт baseline и список open risks. Acceptance отделяет внедрение от recurring service. Offboarding зеркально удаляет доступ, передаёт artifacts и учитывает retention backups.

## Разобранный пример

```text
Won → pre-onboarding gate → technical onboarding
→ acceptance → operation/review → renewal или offboarding
```

### Как читать пример

- `Won → pre-onboarding gate → technical onboarding` — None
- `→ acceptance → operation/review → renewal или offboarding` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Проведите mock-client через lifecycle.
2. Создайте access matrix и baseline.
3. Выполните offboarding и найдите orphan access.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| SLA начался до acceptance | Это сужает область поиска, но не доказывает единственную причину | риск ложного breach. |
| Секреты в Kaiten | Это сужает область поиска, но не доказывает единственную причину | перенести в Vaultwarden и ротировать. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Подписанный клиент ещё не должен автоматически попадать под SLA.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `acceptance` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `offboarding` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `secret lifecycle` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «SLA начался до acceptance» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/operations/CLIENT_LIFECYCLE.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/operations/CLIENT_LIFECYCLE.md)
- [docs/onboarding/README.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/onboarding/README.md)

- [Русскоязычный видеопоиск: Onboarding, steady state и offboarding](https://www.youtube.com/results?search_query=Onboarding%2C+steady+state+%D0%B8+offboarding+%D0%BD%D0%B0+%D1%80%D1%83%D1%81%D1%81%D0%BA%D0%BE%D0%BC)

## Условие перехода

Глава завершена, если вы можете связно объяснить `acceptance`, `offboarding`, `secret lifecycle`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
