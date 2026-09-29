# 20. Метрики и Prometheus

> **Учебная ситуация.** Dashboard красивый, но Owner не понимает, что измеряет график.

Предыдущая глава: [глава 19](./19-smtp-dns-и-stalwart-postbox.md).

## Модель, которую нужно построить

Metric sample состоит из имени, labels, timestamp и value. Counter только растёт до restart; gauge может расти и падать; histogram распределяет observations по buckets.

Prometheus сам scrape targets. `up=1` означает успешный scrape, а не исправность бизнес-функции.

Каждая комбинация labels создаёт series. User ID или URL с уникальным query ведёт к cardinality explosion.

## Термины в рабочем смысле

### metric

Числовое наблюдение с именем, labels и timestamp. Оно не содержит автоматически порог, приоритет или договорное обещание.

### counter

Metric, которая монотонно растёт до reset процесса; скорость считают через `rate`, а не вычитанием случайных точек.

### cardinality

Число уникальных label sets. Неограниченные user/request значения создают новые series и нагружают TSDB.

## Что происходит внутри

Exporter не отправляет данные в Prometheus: Prometheus сам делает scrape. Query `rate(counter[5m])` оценивает среднюю скорость с учётом reset. Histogram quantile вычисляется по агрегированным buckets; без правильного `le` и одинаковых dimensions результат бессмыслен.

## Разобранный пример

```promql
up{job="backend"}
rate(http_requests_total{status=~"5.."}[5m])
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
```

### Как читать пример

- `up{job="backend"}` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `rate(http_requests_total{status=~"5.."}[5m])` — `rate` оценивает скорость counter по диапазону и учитывает reset; instant selector counter показывает накопленное значение.
- `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` — `rate` оценивает скорость counter по диапазону и учитывает reset; instant selector counter показывает накопленное значение.

## Практикум

1. Найдите targets и scrape errors.
2. Постройте три запроса.
3. Объясните каждую функцию и label matcher.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| No data | Это сужает область поиска, но не доказывает единственную причину | target/selector/retention, а не нулевое значение. |
| Высокий CPU Prometheus | Это сужает область поиска, но не доказывает единственную причину | проверить cardinality и query. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Dashboard красивый, но Owner не понимает, что измеряет график.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `metric` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `counter` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `cardinality` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «No data» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [deploy/yandex/monitoring/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/deploy/yandex/monitoring/docker-compose.yml)
- [deploy/yandex/monitoring/prometheus/](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/deploy/yandex/monitoring/prometheus/)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

## Условие перехода

Глава завершена, если вы можете связно объяснить `metric`, `counter`, `cardinality`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
