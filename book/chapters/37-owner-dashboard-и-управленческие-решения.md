# 37. владелец проекта dashboard и управленческие решения

> **Учебная ситуация.** Метрик много, но ни одна не меняет решение.

## Главное

MRR — нормализованная recurring выручка; вклад в покрытие MRR лучше показывает ресурс на постоянные расходы. ARR = MRR×12 только при стабильной модели.

Logo churn считает клиентов, MRR churn — потерянную выручку. NRR учитывает expansion и contraction; cohort не смешивает клиентов разного возраста.

CAC включает согласованный набор acquisition costs. Payback = CAC / monthly вклад в покрытие, а не выручка. LTV молодого бизнеса — гипотеза с sensitivity.

## Как это работает

Dashboard начинается со словаря метрик. Для каждой фиксируются source tables, formula, period, cohort и action threshold. Выручка metrics сравниваются с вклад в покрытие и доступное время команды; иначе рост MRR может маскировать убыточную перегрузку.

## Пример

```text
Sales velocity = opportunities × win_rate × average_deal / sales_cycle_days
CAC payback = CAC / monthly вклад в покрытие
NRR = (start MRR − churn − contraction + expansion) / start MRR
```

## Практикум

1. Постройте 12 месяцев synthetic data.
2. Рассчитайте метрики вручную и формулами.
3. Для каждого порога назначьте решение.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Высокий MRR при низкой вклад в покрытие | рост может ухудшать деньги на счёте. |
| Средний CAC без определения расходов | несравним. |

## Источники проекта

- [technical/BUSINESS_MODEL.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/technical/BUSINESS_MODEL.md)
- [commercial/SALES_FUNNEL.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/commercial/SALES_FUNNEL.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

