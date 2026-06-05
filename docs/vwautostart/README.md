# VM Watcher — автозапуск Yandex Cloud VM

Windows-служба, которая мониторит VM на Yandex Cloud и автоматически запускает её, если она остановлена.

## Как работает

1. Каждые 5 минут пингует публичный IP VM (`93.77.184.219`)
2. Если 5 пингов подряд не прошли — проверяет статус VM через `yc compute instance get`
3. Если VM **stopped** — отправляет `yc compute instance start` и уведомление в Telegram
4. Если VM **running** но не отвечает — уведомление «проблема сети»
5. Когда VM восстанавливается — уведомление «VM restored»

## Состав

| Файл | Назначение |
|------|-----------|
| `watcher.ps1` | Основной скрипт — пинг, проверка YC, автозапуск, Telegram-алерты |
| `tray.ps1` | Иконка в системном трее — Start/Stop, автозапуск, Exit |
| `install.ps1` | Установка — создаёт 2 задачи в Task Scheduler |
| `uninstall.ps1` | Удаление — останавливает процессы и удаляет задачи |

## Требования

- Windows 10+
- `yc` CLI с настроенным профилем (`yc config list` должен показывать token, cloud-id, folder-id)
- Доступ к интернету (ping + YC API + Telegram API)

## Установка

1. Скопируйте папку `vwautostart` в любое место на диске
2. Откройте PowerShell от имени администратора
3. Запустите:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
```

Создаются 2 задачи Task Scheduler:

| Задача | Аккаунт | Триггер | Описание |
|--------|---------|---------|----------|
| `MSPVMWatcher` | NT AUTHORITY\SYSTEM | При загрузке Windows | Watcher — пинг и автозапуск VM |
| `MSPVMWatcherTray` | Текущий пользователь | При входе в систему | Иконка в трее |

## Трей

Иконка в системном трее:

- **Зелёная** (info) — watcher запущен
- **Жёлтая** (warning) — watcher остановлен
- Дабл-клик — Start/Stop
- Правая кнопка → меню:
  - **Start / Stop** — запустить или остановить watcher
  - **Autostart with Windows** — чекбокс, включает/выключает автозапуск задачи
  - **Exit** — закрыть трей (watcher продолжает работать)

## Удаление

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File uninstall.ps1
```

## Лог

Файл `vm-watcher.log` создаётся рядом со скриптами. Пример:

```
[2026-06-05 23:56:58] === VM Watcher started ===
[2026-06-05 23:56:58] Target=93.77.184.219 Interval=300s Threshold=5 VM=fhmab2qg10esn09j0na2
[2026-06-05 23:56:59] PING OK
[2026-06-06 00:01:59] PING OK
[2026-06-06 00:06:59] PING FAIL (1/5)
[2026-06-06 00:11:59] PING FAIL (2/5)
...
[2026-06-06 00:26:59] PING FAIL (5/5)
[2026-06-06 00:26:59] Threshold reached - checking VM via YC CLI
[2026-06-06 00:27:00] VM status: stopped
[2026-06-06 00:27:00] VM STOPPED - sending start command
[2026-06-06 00:27:00] VM START command sent for fhmab2qg10esn09j0na2
[2026-06-06 00:27:00] Telegram alert sent
```

## Параметры watcher.ps1

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `$Target` | `93.77.184.219` | Публичный IP VM |
| `$IntervalSeconds` | `300` | Интервал проверки (секунды) |
| `$FailThreshold` | `5` | Кол-во ошибок для срабатывания |
| `$VmId` | `fhmab2qg10esn09j0na2` | ID инстанса Yandex Cloud |

## Мульти-пользователь

Watcher работает от `NT AUTHORITY\SYSTEM` — не зависит от учётной записи. Пути относительные (`$PSScriptRoot`), скрипты можно установить из любой учётки. Трей запускается отдельно при логоне текущего пользователя.
