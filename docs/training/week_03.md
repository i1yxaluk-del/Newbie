# Week 3 · Monitoring (Prometheus + Grafana)

## Цель

Уметь читать Grafana dashboards, понимать alert-правила, отвечать на
первые alerts без помощи.

## Задачи

- [ ] Прочитать `technical/0_Common/monitoring/prometheus.yml` и все
      правила в `rules/`.
- [ ] Сеанс с owner: 1 час про PromQL. Упражнения на `rate()`, `avg()`,
      `by(...)`.
- [ ] Построить в тестовом Grafana свой dashboard: CPU, memory,
      disk-usage, network для одной VM.
- [ ] Разобрать 3 последних alert'а в истории, что с ними делали.

## Production задачи

- [ ] Взять любой non-critical alert (NodeDown / HighCPU в off-hours),
      отреагировать самостоятельно, написать write-up в Kaiten.
- [ ] Настроить новый alert (например: SSH brute-force attempts) и
      протестировать.

## Read

- Prometheus operating guide: "First steps" + "Querying basics".
- [PromLabs promql-tutorial](https://promlabs.com/promql-cheat-sheet/)
  на пол-часа.

## Check-in

1. Различие `rate()` vs `irate()` vs `increase()`?
2. Как устроен Alertmanager routing (`route` tree)?
3. Зачем `for: 10m` в правиле alert'а?

## DoD

- Развёрнут свой Grafana dashboard (по скриншоту show-and-tell).
- Отреагировал на 1+ реальный alert самостоятельно.
- Добавил 1 новое alert-правило.
