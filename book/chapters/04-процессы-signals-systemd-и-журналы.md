# 4. Процессы, signals, systemd и журналы

> **Учебная ситуация.** Caddy установлен, но после reboot сайт не поднялся.

## Главное

Процесс — выполняющийся экземпляр программы с PID, окружением и открытыми descriptors. Exit code относится к завершившемуся процессу.

Signal просит процесс выполнить действие; SIGTERM даёт шанс завершиться корректно, SIGKILL — нет.

systemd хранит желаемое состояние unit и зависимости. `restart` запускает старое определение; после изменения unit нужен `daemon-reload`.

## Слова, которые встретятся дальше

### процесс

Запущенный экземпляр программы: address space, PID, секрет доступаs, environment и file descriptors. Service может породить несколько процессов.

### signal

Асинхронное уведомление процессу. SIGTERM допускает обработчик и graceful shutdown; SIGKILL выполняется ядром и не даёт очистить состояние.

### unit

Декларация systemd о том, как создать и контролировать ресурс. Active unit не доказывает, что внешний пользователь получает корректный ответ.

## Как это работает

systemd создаёт процесс по ExecStart, наблюдает его exit и применяет Restart. Environment service формируется unit-файлом, EnvironmentFile и manager environment, а не вашим `.bashrc`. Journal объединяет stdout/stderr и metadata unit; фильтр `-b` ограничивает текущей загрузкой.

## Пример

```bash
systemctl status caddy --no-pager
systemctl cat caddy
journalctl -u caddy -b --no-pager -n 100
systemctl show caddy -p Environment -p ExecStart
```

### Что здесь происходит

- `systemctl status caddy --no-pager` — `systemctl` обращается к systemd manager; `status` показывает unit сохранённые данные и последние сообщения, но не внешний user path.
- `systemctl cat caddy` — `systemctl` обращается к systemd manager; `status` показывает unit сохранённые данные и последние сообщения, но не внешний user path.
- `journalctl -u caddy -b --no-pager -n 100` — `journalctl` читает structured journal; `-u` фильтрует unit, `-b` — boot, `-n` — последние записи.
- `systemctl show caddy -p Environment -p ExecStart` — `systemctl` обращается к systemd manager; `status` показывает unit сохранённые данные и последние сообщения, но не внешний user path.

## Практикум

1. Создайте учебный unit для `python -m http.server`.
2. Сломайте путь ExecStart и найдите код завершения.
3. Исправьте unit, выполните daemon-reload и enable.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Unit active, сайт недоступен | проверить сетевое подключение и firewall. |
| Переменная есть в shell, но нет в service | systemd не наследует интерактивное окружение. |


## Проверьте себя

1. Объясните `процесс` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `signal` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `unit` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Unit active, сайт недоступен» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [развёртывание/yandex/setup-on-vm.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/setup-on-vm.sh)
- [docs/развёртываниеment/DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/DEPLOY_RUNBOOK.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

