# 18. Полный развёртывание MSPShield

> **Учебная ситуация.** Нужно развернуть систему на чистой VM и понимать каждый gate.

## Главное

Порядок уменьшает число неизвестных: base VM → code → env → preflight → application → monitoring → Caddy → DNS → external проверки.

Preflight проверяет наличие env, BOM/CRLF, обязательные ключи, Compose render, secure entrypoint и небезопасный SSH bypass; `--fix` имеет ограниченные side effects и резервная копия.

DNS переключается последним, после проверки нового IP из целевого региона. Иначе исправная VM может быть недоступна клиентам.

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

## Практикум

1. Выполните развёртывание на пустой VM.
2. После каждого шага снимите сохранённые данные подтверждение.
3. Проведите внешний TCP/TLS/HTTP smoke test до DNS switch.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 503 | проверить provisioning-заглушку и MSP_DOMAIN. |
| Пустой webroot | frontend сборка/setup не выполнен. |

## Источники проекта

- [docs/развёртываниеment/DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/DEPLOY_RUNBOOK.md)
- [scripts/развёртываниеment/preflight.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/scripts/развёртываниеment/preflight.sh)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

