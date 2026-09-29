# 37. владелец проекта dashboard и управленческие решения

> **Учебная ситуация.** Метрик много, но ни одна не меняет решение.

## Главное

MRR — нормализованная recurring revenue; contribution MRR лучше показывает ресурс на fixed costs. ARR = MRR×12 только при стабильной модели.

Logo churn считает клиентов, MRR churn — потерянную выручку. NRR учитывает expansion и contraction; cohort не смешивает клиентов разного возраста.

CAC включает согласованный набор acquisition costs. Payback = CAC / monthly contribution, а не revenue. LTV молодого бизнеса — гипотеза с sensitivity.

## Слова, которые встретятся дальше

### MRR

Нормализованная месячная повторяющаяся выручка; разовые onboarding и проекты в MRR не включаются.

### NRR

Отношение recurring revenue существующей когорты после churn/contraction/expansion к её начальному MRR.

### CAC

Согласованный набор затрат на привлечение, делённый на число новых клиентов; состав расходов должен быть стабильным.

### LTV

Оценка будущей contribution за жизнь клиента. В молодом бизнесе это сценарная гипотеза, а не надёжный факт.

## Как это работает

Dashboard начинается со словаря метрик. Для каждой фиксируются source tables, formula, period, cohort и action threshold. Revenue metrics сравниваются с contribution и доступное время команды; иначе рост MRR может маскировать убыточную перегрузку.

## Пример

```text
Sales velocity = opportunities × win_rate × average_deal / sales_cycle_days
CAC payback = CAC / monthly contribution
NRR = (start MRR − churn − contraction + expansion) / start MRR
```

### Что здесь происходит

- `Sales velocity = opportunities × win_rate × average_deal / sales_cycle_days` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `CAC payback = CAC / monthly contribution` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `NRR = (start MRR − churn − contraction + expansion) / start MRR` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Постройте 12 месяцев synthetic data.
2. Рассчитайте метрики вручную и формулами.
3. Для каждого порога назначьте решение.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Высокий MRR при низкой contribution | рост может ухудшать cash. |
| Средний CAC без определения расходов | несравним. |


## Проверьте себя

1. Объясните `MRR` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `NRR` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `CAC` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Высокий MRR при низкой contribution» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [technical/BUSINESS_MODEL.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/technical/BUSINESS_MODEL.md)
- [commercial/SALES_FUNNEL.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/commercial/SALES_FUNNEL.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

