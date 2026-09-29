# 38. Финальный бизнес-capstone

> **Учебная ситуация.** Нужно принять или отклонить реального по структуре клиента и защитить решение.

Предыдущая глава: [глава 37](./37-owner-dashboard-и-управленческие-решения.md).

## Модель, которую нужно построить

Capstone объединяет technical feasibility, capacity, unit economics, sales ethics и contract boundaries.

Хорошее решение может быть `waitlist` или `no`. Продажа, разрушающая SLA существующих клиентов, не является успехом.

Каждая цифра имеет источник и sensitivity; каждое обещание — owner, процесс и evidence.

## Термины в рабочем смысле

### capstone

Сквозная работа без пошагового рецепта, проверяющая перенос знаний, recovery и способность обосновать решения.

### capacity

Доступный объём работы после non-billable времени и reserve. Проданная работа не создаёт capacity.

### contribution

Revenue услуги минус её прямые переменные затраты, оценённый труд, transaction costs и reserve; источник покрытия fixed costs и прибыли.

### perimeter

Закрытый перечень объектов, операций и зависимостей, на которые распространяется услуга. Сетевая доступность не включает объект автоматически.

## Что происходит внутри

Decision pack должен быть воспроизводим: другой reviewer пересчитывает effort, price и margin из inputs. Unknowns превращаются в conditions или paid assessment. Итог accept/waitlist/no-fit защищает существующих клиентов и не подменяется желанием закрыть продажу.

## Разобранный пример

```text
ICP → discovery → perimeter → architecture → effort/capacity
→ price/margin → proposal → contract → onboarding 90 days
→ owner dashboard
```

### Как читать пример

- `ICP → discovery → perimeter → architecture → effort/capacity` — None
- `→ price/margin → proposal → contract → onboarding 90 days` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `→ owner dashboard` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Получите mock case с неполными данными.
2. Задайте вопросы, не дополняя факты.
3. Подготовьте decision pack и защитите accept/waitlist/no-fit.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Gold без responders/drills/legal review | Это сужает область поиска, но не доказывает единственную причину | только capacity check. |
| Margin проходит только при нулевой цене Owner time | Это сужает область поиска, но не доказывает единственную причину | модель отклонить. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Нужно принять или отклонить реального по структуре клиента и защитить решение.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `capstone` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `capacity` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `contribution` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Gold без responders/drills/legal review» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [commercial/README.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/commercial/README.md)
- [contracts/MSP_SERVICE_AGREEMENT.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/contracts/MSP_SERVICE_AGREEMENT.md)
- [docs/operations/CLIENT_LIFECYCLE.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/operations/CLIENT_LIFECYCLE.md)

- [Русскоязычный видеопоиск: Финальный бизнес-capstone](https://www.youtube.com/results?search_query=%D0%A4%D0%B8%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9+%D0%B1%D0%B8%D0%B7%D0%BD%D0%B5%D1%81-capstone+%D0%BD%D0%B0+%D1%80%D1%83%D1%81%D1%81%D0%BA%D0%BE%D0%BC)

## Условие перехода

Глава завершена, если вы можете связно объяснить `capstone`, `capacity`, `contribution`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
