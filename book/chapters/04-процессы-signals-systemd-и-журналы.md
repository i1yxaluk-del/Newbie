# 4. Процессы, signals, systemd и журналы

> **Учебная ситуация.** Caddy установлен, но после reboot сайт не поднялся.

## Главное

Процесс — выполняющийся экземпляр программы с PID, окружением и открытыми descriptors. Exit code относится к завершившемуся процессу.

Signal просит процесс выполнить действие; SIGTERM даёт шанс завершиться корректно, SIGKILL — нет.

systemd хранит желаемое состояние unit и зависимости. `restart` запускает старое определение; после изменения unit нужен `daemon-reload`.

## Как это работает

systemd создаёт процесс по ExecStart, наблюдает его exit и применяет Restart. Environment service формируется unit-файлом, EnvironmentFile и manager environment, а не вашим `.bashrc`. Journal объединяет stdout/stderr и служебные данные unit; фильтр `-b` ограничивает текущей загрузкой.

## Пример

```bash
systemctl status caddy --no-pager
systemctl cat caddy
journalctl -u caddy -b --no-pager -n 100
systemctl show caddy -p Environment -p ExecStart
```

## Практикум

1. Создайте учебный unit для `python -m http.server`.
2. Сломайте путь ExecStart и найдите код завершения.
3. Исправьте unit, выполните daemon-reload и enable.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Unit active, сайт недоступен | проверить сетевое подключение и firewall. |
| Переменная есть в shell, но нет в service | systemd не наследует интерактивное окружение. |

## Источники проекта

- [развёртывание/yandex/setup-on-vm.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/setup-on-vm.sh)
- [docs/deployment/DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/DEPLOY_RUNBOOK.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

