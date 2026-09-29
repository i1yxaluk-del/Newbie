# 38. Финальный бизнес-capstone

> **Учебная ситуация.** Нужно принять или отклонить реального по структуре клиента и защитить решение.

## Главное

Capstone объединяет technical feasibility, доступное время команды, unit economics, sales ethics и contract boundaries.

Хорошее решение может быть `waitlist` или `no`. Продажа, разрушающая SLA существующих клиентов, не является успехом.

Каждая цифра имеет источник и sensitivity; каждое обещание — владелец, процесс и подтверждение.

## Слова, которые встретятся дальше

### capstone

Сквозная работа без пошагового рецепта, проверяющая перенос знаний, recovery и способность обосновать решения.

### доступное время команды

Доступный объём работы после non-billable времени и reserve. Проданная работа не создаёт доступное время команды.

### contribution

Revenue услуги минус её прямые переменные затраты, оценённый труд, transaction costs и reserve; источник покрытия fixed costs и прибыли.

### perimeter

Закрытый перечень объектов, операций и зависимостей, на которые распространяется услуга. Сетевая доступность не включает объект автоматически.

## Как это работает

Decision pack должен быть воспроизводим: другой reviewer пересчитывает effort, price и margin из inputs. Unknowns превращаются в conditions или paid assessment. Итог accept/waitlist/no-fit защищает существующих клиентов и не подменяется желанием закрыть продажу.

## Пример

```text
ICP → первая встреча → perimeter → architecture → effort/доступное время команды
→ price/margin → proposal → contract → onboarding 90 days
→ владелец dashboard
```

### Что здесь происходит

- `ICP → первая встреча → perimeter → architecture → effort/доступное время команды` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `→ price/margin → proposal → contract → onboarding 90 days` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `→ владелец dashboard` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Получите mock case с неполными данными.
2. Задайте вопросы, не дополняя факты.
3. Подготовьте decision pack и защитите accept/waitlist/no-fit.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Gold без responders/drills/legal review | только доступное время команды check. |
| Margin проходит только при нулевой цене владелец проекта time | модель отклонить. |


## Проверьте себя

1. Объясните `capstone` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `доступное время команды` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `contribution` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Gold без responders/drills/legal review» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [commercial/README.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/commercial/README.md)
- [contracts/MSP_SERVICE_AGREEMENT.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/contracts/MSP_SERVICE_AGREEMENT.md)
- [docs/operations/CLIENT_LIFECYCLE.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/operations/CLIENT_LIFECYCLE.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

