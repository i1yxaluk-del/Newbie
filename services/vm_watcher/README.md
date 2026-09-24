# VM Watcher

[← Сервисы](../README.md) · [Главная](../../README.md) · [Deployment](../../docs/deployment/README.md)

Windows tray-сервис для внешней проверки VM. Он использует пользовательский config и проверяет TCP/443, а не делает вывод о доступности только по ICMP.

## Файлы

| Файл | Назначение |
|---|---|
| `config.example.json` | пример конфигурации без секретов |
| `install.ps1` | установка |
| `watcher.ps1` | основная проверка |
| `tray.ps1` | tray-интерфейс |
| `uninstall.ps1` | удаление |

## Порядок

1. Скопировать `config.example.json` в пользовательский config вне Git.
2. Заполнить адрес VM и проверяемый HTTPS endpoint.
3. Проверить команду вручную без вывода секретов.
4. Выполнить `install.ps1` от требуемого пользователя.
5. Подтвердить healthy и simulated failure.

VM Watcher дополняет Prometheus/Alertmanager, но не заменяет [`../../docs/runbooks/README.md`](../../docs/runbooks/README.md) и внешний production scan.
