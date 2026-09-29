# 20. Метрики и Prometheus

> **Учебная ситуация.** Dashboard красивый, но владелец проекта не понимает, что измеряет график.

## Главное

Metric sample состоит из имени, labels, timestamp и value. Counter только растёт до restart; gauge может расти и падать; histogram распределяет observations по buckets.

Prometheus сам scrape targets. `up=1` означает успешный scrape, а не исправность бизнес-функции.

Каждая комбинация labels создаёт series. User ID или URL с уникальным query ведёт к cardinality explosion.

## Как это работает

Exporter не отправляет данные в Prometheus: Prometheus сам делает scrape. Query `rate(counter[5m])` оценивает среднюю скорость с учётом перенос указателя версии. Histogram quantile вычисляется по агрегированным buckets; без правильного `le` и одинаковых dimensions результат бессмыслен.

## Пример

```promql
up{job="backend"}
rate(http_requests_total{status=~"5.."}[5m])
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
```

## Практикум

1. Найдите targets и scrape errors.
2. Постройте три запроса.
3. Объясните каждую функцию и label matcher.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| No data | target/selector/срок хранения, а не нулевое значение. |
| Высокий CPU Prometheus | проверить cardinality и query. |

## Источники проекта

- [развёртывание/yandex/monitoring/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/monitoring/docker-compose.yml)
- [развёртывание/yandex/monitoring/prometheus/](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/monitoring/prometheus/)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

