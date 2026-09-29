# 18. Полный развёртывание MSPShield

> **Учебная ситуация.** Нужно развернуть систему на чистой VM и понимать каждый gate.

## Главное

Порядок уменьшает число неизвестных: base VM → code → env → preflight → application → monitoring → Caddy → DNS → external checks.

Preflight проверяет наличие env, BOM/CRLF, обязательные ключи, Compose render, secure entrypoint и небезопасный SSH bypass; `--fix` имеет ограниченные side effects и резервная копия.

DNS переключается последним, после проверки нового IP из целевого региона. Иначе исправная VM может быть недоступна клиентам.

## Слова, которые встретятся дальше

### preflight

Проверка prerequisites до side-effecting развёртывание. Хороший preflight завершает процесс до частично поднятой системы.

### cutover

Момент перевода production traffic или authority на новую среду. Требует критериев go/no-go и rollback.

### подтверждение

Минимальный проверяемый артефакт: timestamp, exit code, hash, запрос/ответ, metric или подписанный документ. Скриншот зелёной панели без target и времени — слабое подтверждение.

## Как это работает

Preflight уменьшает вероятность частичного развёртывание, но не заменяет runtime verification. После `up` отдельно проверяются процесс health, внутренний API, proxy, external network, предупреждение delivery и восстановление. DNS переключается только когда новая среда прошла эти независимые gates.

## Пример

```bash
cd /opt/msp/Newbie
sudo bash scripts/развёртываниеment/preflight.sh --fix
cd развёртывание/yandex && docker compose up -d
cd monitoring && docker compose up -d
curl -fsS http://127.0.0.1:8001/api/health
```

### Что здесь происходит

- `cd /opt/msp/Newbie` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `sudo bash scripts/развёртываниеment/preflight.sh --fix` — `sudo` запускает следующую программу с повышенной effective identity; shell уже обработал кавычки, glob и redirection.
- `cd развёртывание/yandex && docker compose up -d` — `up` приводит runtime к описанной модели; `-d` отсоединяет terminal, `--force-recreate` пересоздаёт container.
- `cd monitoring && docker compose up -d` — `up` приводит runtime к описанной модели; `-d` отсоединяет terminal, `--force-recreate` пересоздаёт container.
- `curl -fsS http://127.0.0.1:8001/api/health` — `curl` создаёт реальный HTTP/TLS request. `-f` делает HTTP 4xx/5xx ненулевым exit, `-sS` скрывает progress, но оставляет ошибки.

## Практикум

1. Выполните развёртывание на пустой VM.
2. После каждого шага снимите сохранённые данные подтверждение.
3. Проведите внешний TCP/TLS/HTTP smoke test до DNS switch.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 503 | проверить provisioning-заглушку и MSP_DOMAIN. |
| Пустой webroot | frontend build/setup не выполнен. |


## Проверьте себя

1. Объясните `preflight` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `cutover` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `подтверждение` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «503» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/развёртываниеment/DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/DEPLOY_RUNBOOK.md)
- [scripts/развёртываниеment/preflight.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/scripts/развёртываниеment/preflight.sh)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

