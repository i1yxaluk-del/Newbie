# 7. HTTP, TLS и reverse proxy

> **Учебная ситуация.** Caddy отдаёт 503 после чистой установки.

## Главное

HTTP request содержит method, target, headers и body; response — status, headers и body. 503 означает, что HTTP-ответ уже получен.

TLS проверяет владение private key и цепочку доверия. SNI позволяет выбрать сертификат по hostname до HTTP.

Reverse proxy принимает внешний TLS и создаёт отдельное соединение к upstream. Ошибка proxy и ошибка backend находятся на разных участках.

## Как это работает

Клиентский сертификат относится к hostname, а не к адресу backend. Caddy может успешно завершить TLS и вернуть собственный 503 без обращения к FastAPI. Поэтому сравнение `curl 127.0.0.1:8001` и `curl https://domain` локализует неисправность между приложением и proxy/front door.

## Пример

```caddy
{$MSP_DOMAIN} {
  handle /api/* { reverse_proxy 127.0.0.1:8001 }
  root * /var/www/landing
  file_server
}
```

## Практикум

1. Проверьте `caddy validate`.
2. Сравните curl к backend и через Caddy.
3. Оставьте заглушку cloud-init и объясните 503, затем замените конфигурацию.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| TLS error до HTTP | проверять DNS/SNI/certificate. |
| 502 | proxy не получил корректный ответ upstream; 503 может быть явной заглушкой. |

## Источники проекта

- [развёртывание/yandex/Caddyfile](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/Caddyfile)
- [docs/развёртываниеment/DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/DEPLOY_RUNBOOK.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

