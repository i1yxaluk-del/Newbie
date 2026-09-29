# 18. Полный deploy MSPShield

> **Учебная ситуация.** Нужно развернуть систему на чистой VM и понимать каждый gate.

Предыдущая глава: [глава 17](./17-облако-и-vm-с-нуля.md).

## Модель, которую нужно построить

Порядок уменьшает число неизвестных: base VM → code → env → preflight → application → monitoring → Caddy → DNS → external checks.

Preflight проверяет наличие env, BOM/CRLF, обязательные ключи, Compose render, secure entrypoint и небезопасный SSH bypass; `--fix` имеет ограниченные side effects и backup.

DNS переключается последним, после проверки нового IP из целевого региона. Иначе исправная VM может быть недоступна клиентам.

## Термины в рабочем смысле

### preflight

Проверка prerequisites до side-effecting deploy. Хороший preflight завершает процесс до частично поднятой системы.

### cutover

Момент перевода production traffic или authority на новую среду. Требует критериев go/no-go и rollback.

### evidence

Минимальный проверяемый артефакт: timestamp, exit code, hash, запрос/ответ, metric или подписанный документ. Скриншот зелёной панели без target и времени — слабое evidence.

## Что происходит внутри

Preflight уменьшает вероятность частичного deploy, но не заменяет runtime verification. После `up` отдельно проверяются process health, внутренний API, proxy, external network, alert delivery и restore. DNS переключается только когда новая среда прошла эти независимые gates.

## Разобранный пример

```bash
cd /opt/msp/Newbie
sudo bash scripts/deployment/preflight.sh --fix
cd deploy/yandex && docker compose up -d
cd monitoring && docker compose up -d
curl -fsS http://127.0.0.1:8001/api/health
```

### Как читать пример

- `cd /opt/msp/Newbie` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `sudo bash scripts/deployment/preflight.sh --fix` — `sudo` запускает следующую программу с повышенной effective identity; shell уже обработал кавычки, glob и redirection.
- `cd deploy/yandex && docker compose up -d` — `up` приводит runtime к описанной модели; `-d` отсоединяет terminal, `--force-recreate` пересоздаёт container.
- `cd monitoring && docker compose up -d` — `up` приводит runtime к описанной модели; `-d` отсоединяет terminal, `--force-recreate` пересоздаёт container.
- `curl -fsS http://127.0.0.1:8001/api/health` — `curl` создаёт реальный HTTP/TLS request. `-f` делает HTTP 4xx/5xx ненулевым exit, `-sS` скрывает progress, но оставляет ошибки.

## Практикум

1. Выполните deploy на пустой VM.
2. После каждого шага снимите state evidence.
3. Проведите внешний TCP/TLS/HTTP smoke test до DNS switch.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 503 | Это сужает область поиска, но не доказывает единственную причину | проверить provisioning-заглушку и MSP_DOMAIN. |
| Пустой webroot | Это сужает область поиска, но не доказывает единственную причину | frontend build/setup не выполнен. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Нужно развернуть систему на чистой VM и понимать каждый gate.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `preflight` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `cutover` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `evidence` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «503» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/deployment/DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/DEPLOY_RUNBOOK.md)
- [scripts/deployment/preflight.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/scripts/deployment/preflight.sh)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

## Условие перехода

Глава завершена, если вы можете связно объяснить `preflight`, `cutover`, `evidence`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
