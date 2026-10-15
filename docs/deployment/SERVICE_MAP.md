# Карта сервиса и воспроизводимость

## Границы контуров

| Контур | Источник конфигурации | Состояние/зависимости | Что доказывает готовность |
|---|---|---|---|
| Landing | `frontend/` → CRA build → `/var/www/landing`, host Caddy | домен, DNS, TLS, Node 20/Yarn 1.22.22 | build + HTTPS + форма на разрешённом тестовом target |
| Lead API | `deploy/yandex/docker-compose.yml`, `secure_server:app` | Mongo; `backend/.env`; один worker | health, сохранение, outbox pending/retry, доставка в утверждённую CRM |
| Monitoring | `deploy/yandex/monitoring/` | внешняя `msp_default`, локальная monitoring network, Prometheus/Grafana/Alertmanager | проверка targets/rules + реальный alert/resolved в основной и резервный канал |
| MAX userbot | `services/max_alerter/`, monitoring Compose | `/session/max.db`, `/data`, ручная авторизация оператором | auth check без SMS и end-to-end alert; HTTP health недостаточен |
| Matrix alert | `services/matrix_alerter/`, monitoring Compose | отдельный Matrix/Synapse/MAS, пользователь и комнаты | доставка в нужные комнаты; отказ homeserver не должен лишать последнего канала |
| Vaultwarden | application Compose | persistent volume, личные MFA/recovery; тот же host — общая точка отказа | вход, безопасная аварийная копия recovery вне VM, прикладной restore |
| Почта (опционально) | Stalwart profile `mail` | оба тома, DNS/MX/PTR/SPF/DKIM/DMARC; direct MX либо явно выбранный relay | отправка/приём/спам-проверка и восстановление обоих томов |
| Matrix/MAS/RTC/invite и другие сервисы | отдельные `deploy/matrix*`, `deploy/mas`, `deploy/rtc`, `deploy/xmpp*` и systemd | не входят автоматически в основной Compose или его backup | отдельный inventory, версия, БД/ключи, инструкция deploy/rollback/restore и акт проверки |
| Клиентский tenant | подписанный dossier и `technical/` | индивидуальные агенты, VPN, приложения, backup | acceptance конкретного клиента; наличие шаблона в Git не означает развёртывание |

Название `deploy/yandex/` сохранено как путь кода, не свидетельство провайдера. Compose содержит переход Stalwart на direct MX Cloud.ru; фактические VM/provider, DNS, routes и версии сверяются по приватному inventory. Не смешивать Terraform/Ansible из `infra/` с single-VM путём без отдельного решения.

## Потоки и точки отказа

```text
Браузер → Caddy HTTPS → static frontend / API loopback:8001
API → Mongo leads → outbox → утверждённые email/CRM/мессенджеры
Prometheus → Alertmanager → MAX / email / Matrix по фактическому routing
Операторская независимая проверка → TCP/HTTPS → резервное оповещение
Согласованные dump/archives → encrypted restic → независимое хранилище
```

Одна VM объединяет API, мониторинг, доступ и vault: её отказ одновременно уничтожает локальную наблюдаемость. MAX/email/Matrix на той же VM не делают мониторинг независимым. Нужны внешний health-check с другого failure domain, резервный контакт и recovery-коды вне host. Docker network — не граница tenant-изоляции: privileged cAdvisor и Docker socket имеют высокий доверенный доступ. Не подключать клиентские контейнеры к этой сети без проектирования изоляции.

## Контракт развёртывания

Для каждой среды закрытый manifest: provider/регион, owner, commit/tag, digest реально запущенных images, домены/порты, способы доступа, версии Docker/Compose/ОС/restic, env **имена без значений**, место секретов, список active profiles/systemd/timers, тома/БД, backup и restore evidence. Отдельно — причина расхождения с Git и план его устранения. Теги образов и широкие Python ranges не дают битовую воспроизводимость: сохранять digest и состав сборки, проверять registry-доступ и лицензии в РФ до окна изменений.

Порядок: исходный inventory → зафиксированный commit → env из утверждённого хранилища → `docker compose config --quiet` → сборка → основной Compose → monitoring → Caddy/static → health → alert/resolved → backup → clean-room restore → acceptance. `preflight --fix` меняет файлы: сначала review; read-only запуск без `--fix` для приёмки. Основной Compose создаёт `msp_default` до monitoring.

Preflight не является проверкой полного ИБ-соответствия, restore или доставки. До смены DNS провести пробы через тестовый домен/согласованный resolve и отдельный TLS-план; ACME HTTP-01 требует корректного DNS. Не переключать рабочий домен просто ради получения первого сертификата без плана отката.

## Backup: что не следует предполагать

`migration/restic-backup.sh` создаёт логический Mongo dump и архивы Vaultwarden/Stalwart/MAX. Копирование `/opt`/`/etc` само по себе не доказывает согласованный backup PostgreSQL MAS, Synapse, Matrix media, XMPP или RTC. Для каждого активного сервиса добавить database-native dump/consistent snapshot, ключи и прикладной тест; до этого его DR — **Unknown**, не «покрыт общим backup».

Mongo standalone dump при продолжающихся записях не гарантирует межколлекционную транзакционную точку. Для миграции согласовать остановку writers либо другую проверенную consistent backup-стратегию. Не восстанавливать raw live volumes БД. На стенде запрещены реальные ПДн и автоматическая отправка писем/алертов клиентам: новые env, отключённые интеграции, отдельные DNS/network.

## Приёмка и откат

Каждый change: среда/tenant, owner/reviewer, разрешение, окно, исходный manifest, проверенный backup, изменение, expected output, stop-condition, rollback, проверка после отката. Сбой проверки — остановка; предыдущий build/config возвращается с учётом совместимости БД. `compose down -v` не является откатом.

Статус «развёрнуто» присваивается только после проверки в среде. Доказательства без секретов: время/commit, контейнеры/digest, внутренний health, внешняя HTTPS-проверка, alert/resolved, возраст последнего backup, прикладной restore и подписавший проверку. Без доступа к VM эта ревизия подтверждает только код и документацию.
