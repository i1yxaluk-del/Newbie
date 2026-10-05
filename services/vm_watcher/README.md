# VM Watcher

[← Сервисы](../README.md) · [Главная](../../README.md) · [Deployment](../../docs/deployment/README.md)

Windows tray-сервис для внешней проверки VM. Он использует пользовательский config и проверяет TCP/443, а не делает вывод о доступности только по ICMP.

С миграции на **Cloud.ru Evolution** watcher больше не использует `yc.exe`: статус ВМ
читается через REST API Cloud.ru (`GET /api/v1/vms/{id}`). Автозапуск ВМ убран —
Cloud.ru Evolution не публикует эндпоинт старта ВМ (проверено: `/vms/{id}/start`,
`/stop`, `/restart`, `/actions/*` → `Not Found`), а ВМ не является preemptible,
поэтому автозапуск больше не нужен. Если ВМ остановлена — watcher пришлёт алерт
с указанием запустить её в консоли Cloud.ru.

## Файлы

| Файл | Назначение |
|---|---|
| `config.example.json` | пример конфигурации без секретов |
| `install.ps1` | установка |
| `watcher.ps1` | основная проверка |
| `tray.ps1` | tray-интерфейс |
| `uninstall.ps1` | удаление |

## Config

| Поле | Назначение |
|---|---|
| `target` | публичный адрес VM (`45.132.176.143`) |
| `port` | проверяемый TCP-порт (по умолчанию 443) |
| `projectId` | ID проекта Cloud.ru (для чтения статуса ВМ) |
| `vmId` | ID ВМ Cloud.ru |
| `intervalSeconds` | период успешной проверки (по умолчанию 300) |
| `failThreshold` | сколько подряд неудач до алерта (по умолчанию 5) |

## Переменные окружения (User scope, вне Git)

| Переменная | Назначение |
|---|---|
| `CLOUDRU_KEY_ID`, `CLOUDRU_KEY_SECRET` | OAuth-ключ Cloud.ru (только чтение статуса) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | алерты |

Если `projectId`/`vmId`/ключи не заданы — watcher работает как чистый TCP-монитор.

## Порядок

1. Скопировать `config.example.json` в пользовательский config вне Git.
2. Заполнить адрес VM и проверяемый HTTPS endpoint.
3. Проверить команду вручную без вывода секретов.
4. Выполнить `install.ps1` от требуемого пользователя.
5. Подтвердить healthy и simulated failure.

> **Важно:** SSH на production VM доступен **только через AmneziaWG** (10.9.0.1),
> снаружи порт 22 закрыт в ufw и Security Group. Диагностика из watcher-алерта
> выполняется через туннель.

VM Watcher дополняет Prometheus/Alertmanager, но не заменяет [`../../docs/runbooks/README.md`](../../docs/runbooks/README.md) и внешний production scan.
