# Мониторинг, Alertmanager и MAX

Метрика — число во времени. Prometheus забирает метрики с targets. Правило превращает условие в alert. Alertmanager группирует события и выбирает получателя. MAX alerter принимает webhook на внутреннем порту 9095 и отправляет сообщение через пользовательскую сессию `pymax`.

MAX-контур требует ручной авторизации. Файл `/session/max.db` равен учётным данным и должен переживать перезагрузку через bind mount. Проверка `auth` без `--authorize` не должна инициировать SMS. Health сервиса не доказывает доставку сообщения; нужен тестовый alert и подтверждение в чате.

Monitoring 24/7 означает постоянный сбор и правила, но не круглосуточную реакцию человека. Окно реакции появляется только в договоре и при наличии ротации.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

## Материал проекта: `docs/MAX_SETUP.md`

<!-- SOURCE docs/MAX_SETUP.md 59035c9969977bd0 -->

## MAX Alerter — каноническая настройка

### 1. Какая архитектура используется

В production алерты доставляются через отдельный webhook-сервис `msp-max-alerter` и пользовательскую сессию MAX:

```text
Prometheus → Alertmanager → POST http://msp-max-alerter:9095/alert
                              ↓
                        pymax userbot
                              ↓
                           MAX chat
```

Авторизация выполняется вручную внутри контейнера:

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

Это **не Telegram MTProto**, не `my.telegram.org`, не `@BotFather` и не официальный MAX Bot API. Старые инструкции с `API_ID`, `API_HASH`, `session.session` и портом `8080` удалены как ошибочные.

### 2. Компоненты

| Компонент | Назначение |
|---|---|
| `services/max_alerter/webhook.py` | принимает Alertmanager webhook `/alert` |
| `services/max_alerter/sender.py` | отправляет в MAX и уведомляет о сбое через резервные каналы |
| `services/max_alerter/auth.py` | вручную создаёт `/session/max.db` |
| `deploy/yandex/monitoring/alertmanager/alertmanager.yml.tmpl` | направляет P1 в `msp-max-alerter:9095` |
| `deploy/yandex/monitoring/docker-compose.override.yml` | подставляет MAX-параметры из `.env`, не из Git |

`backend/integrations/max.py` относится к отдельному боту лидов. Он не является каналом production-алертов и не должен быть получателем Alertmanager при включённом userbot-контуре.

### 3. Обязательные переменные

Создайте `deploy/yandex/monitoring/.env` с правами `600`:

```env
MAX_PHONE=+7XXXXXXXXXX
MAX_CHAT_ID=-00000000000000
ALERTMANAGER_WEBHOOK_TOKEN=<случайная строка не короче 32 байт>
MAX_FAILURE_COOLDOWN=300

## Необязательно: неинтерактивная авторизация (удалить значения после использования!)
## MAX_SMS_CODE=
## MAX_PASSWORD=

## Необязательный Telegram fallback
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

## Необязательное email-уведомление о поломке канала
SMTP_HOST=
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
ALERT_EMAIL_TO=
```

Сгенерировать webhook token:

```bash
openssl rand -hex 32
```

Номер телефона, chat ID, токены и session database запрещено коммитить.

### 4. Первый запуск

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
sudo chmod +x alertmanager/entrypoint.sh
sudo docker compose config >/dev/null
sudo docker compose up -d --build max-alerter alertmanager
```

Проверьте, что контейнер работает, но сессии ещё нет:

```bash
sudo docker ps --filter name=msp-max-alerter
sudo docker exec msp-max-alerter python -m max_alerter.auth
```

Код `2` до первой авторизации ожидаем.

### 5. Ручная авторизация (SMS + пароль 2FA)

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

1. Скрипт берёт номер из `MAX_PHONE`.
2. MAX отправляет код.
3. Оператор вводит код в интерактивном терминале.
4. Если у аккаунта включён пароль 2FA — MAX запрашивает пароль; скрипт спросит его скрытым вводом (`getpass`, символы не отображаются).
5. Сессия сохраняется в `/session/max.db`.
6. Каталог на хосте: `deploy/yandex/monitoring/max-session/`.

Для неинтерактивных прогонов (удалённый запуск без TTY) можно передать значения через окружение:
`MAX_SMS_CODE` и/или `MAX_PASSWORD` в `monitoring/.env` — тогда соответствующий запрос в консоли
пропускается. После использования — удалить значения из `.env` и пересоздать контейнер
(`sudo docker compose up -d --force-recreate max-alerter`).

Никогда не удаляйте рабочую сессию при обычном deploy. Повторная авторизация нужна только при утрате или отзыве сессии.

### 6. Проверка

```bash
## Сессия существует
sudo docker exec msp-max-alerter python -m max_alerter.auth

## Webhook жив
curl -fsS http://127.0.0.1:9095/health

## Alertmanager жив
curl -fsS http://127.0.0.1:9093/-/healthy

## Тестовый webhook из monitoring network
TOKEN=$(sudo awk -F= '$1=="ALERTMANAGER_WEBHOOK_TOKEN"{print $2}' .env)
sudo docker run --rm --network msp-monitoring curlimages/curl:8.10.1 \
  -fsS -X POST http://msp-max-alerter:9095/alert \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"firing","alerts":[{"labels":{"alertname":"ManualTest","severity":"P1","env":"test"},"annotations":{"summary":"Тест MAX","description":"Удалить после проверки"}}]}'
```

Не публикуйте порт `9095` наружу. Он доступен только на `127.0.0.1` и в Docker network.

### 7. Проверка после reboot/deploy

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
sudo docker compose up -d
sudo docker exec msp-max-alerter python -m max_alerter.auth
curl -fsS http://127.0.0.1:9095/health
sudo docker logs msp-max-alerter --tail 100
```

`docker compose restart` не перечитывает `.env`. После изменения переменных используйте:

```bash
sudo docker compose up -d --force-recreate max-alerter alertmanager
```

Сессия переживает перезагрузку ВМ и контейнера: `max.db` — bind-mount на хосте
(`deploy/yandex/monitoring/max-session/max.db`), контейнер стартует автоматически
(`restart: unless-stopped`), повторная авторизация не требуется. Она нужна только
если MAX отзовёт сессию (logout на всех устройствах, смена пароля и т.п.).

### 8. Перенос на новую VM

Переносить нужно каталог сессии отдельно от Git:

```bash
sudo tar czf /root/max-session-backup.tar.gz \
  -C /opt/msp/Newbie/deploy/yandex/monitoring max-session
```

На новой VM восстановить с правами только для root, затем выполнить проверку сессии. Если библиотека отвергает перенесённую сессию — удалить только нерабочий `max.db` и выполнить ручную авторизацию.

### 9. Диагностика

| Симптом | Проверка |
|---|---|
| `manual authorization required` | выполнить команду из раздела 5 |
| `client.unsupported-version` / «Приложение устарело» | обновить `maxapi-python` в `services/max_alerter/requirements.txt` и пересобрать `max-alerter` (см. troubleshooting) |
| HTTP 401 | токены Alertmanager и max-alerter различаются |
| health OK, сообщений нет | проверить `MAX_CHAT_ID` и логи контейнера |
| MAX недоступен | проверить `failed_alerts.log`, Telegram/email fallback |
| после deploy старая конфигурация | `up -d --force-recreate`, не `restart` |
| контейнер не собирается | убедиться, что `services/max_alerter` включён в пакет переноса |

### 10. Безопасность

- `MAX_PHONE` и `MAX_CHAT_ID` только в ignored `.env`;
- `/session/max.db` считать эквивалентом учётных данных;
- webhook token обязателен в production;
- порт 9095 не публиковать в интернет;
- session backup хранить зашифрованно;
- при подозрении на компрометацию отозвать сессию и авторизоваться заново.

### 11. Что является legacy

Следующие элементы не относятся к production MAX alerter:

- `MAX_BOT_TOKEN` и `/api/max/webhook` — бот лидов;
- `platform-api.max.ru` — бот лидов;
- `API_ID`, `API_HASH`, Telethon, `my.telegram.org` — ошибочный Telegram-контент;
- `session.session`, порт `8080`, контейнер `max-alerter` — устаревшие значения.

### 12. Локальная разработка

Без реальной MAX-сессии запускайте unit-тесты форматирования и webhook. Для end-to-end требуется тестовый MAX-аккаунт и ручная авторизация. Long polling в проекте не реализован.


## Материал проекта: `services/max_alerter/README.md`

<!-- SOURCE services/max_alerter/README.md b96a6e33d7232099 -->

## max_alerter — production webhook для MAX

Канонический путь: Alertmanager отправляет webhook на `msp-max-alerter:9095/alert`, сервис доставляет сообщение через вручную авторизованную пользовательскую сессию MAX.

### Запуск

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
sudo docker compose up -d --build max-alerter alertmanager
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

Скрипт спросит SMS-код, а при включённом 2FA — и пароль MAX (ввод скрыт, `getpass`).
Для неинтерактивных прогонов: `MAX_SMS_CODE` / `MAX_PASSWORD` в окружении (см. `docs/MAX_SETUP.md` §5).

Сессия: `/session/max.db`, на хосте — `deploy/yandex/monitoring/max-session/max.db`. Авторизация всегда ручная; сервис не должен сам инициировать SMS.

### Проверка

```bash
sudo docker exec msp-max-alerter python -m max_alerter.auth
curl -fsS http://127.0.0.1:9095/health
sudo docker logs msp-max-alerter --tail 100
```

Полная инструкция и перенос: [`../../docs/MAX_SETUP.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/MAX_SETUP.md).

### Границы

- Это не официальный Bot API и не Telegram MTProto.
- `backend/integrations/max.py` — отдельный бот лидов.
- Номер, chat ID, webhook token и session database не хранятся в Git.
- Telegram используется только как необязательный fallback при отказе MAX.


## Материал проекта: `deploy/yandex/monitoring/docker-compose.yml`

<!-- SOURCE deploy/yandex/monitoring/docker-compose.yml b63f29f24de5ef6b -->

```yaml
# MSPShield monitoring stack. Все секреты берутся из ignored .env.
# Запуск: cd /opt/msp/Newbie/deploy/yandex/monitoring && docker compose up -d
name: msp-monitoring

networks:
  monitoring:
    name: msp-monitoring
    driver: bridge
    ipam:
      config: [{ subnet: 172.20.0.0/24 }]
  msp_default:
    name: msp_default
    external: true

volumes:
  prometheus_data: { name: msp-prometheus-data }
  grafana_data: { name: msp-grafana-data }
  alertmanager_data: { name: msp-alertmanager-data }
  max-alerter-data: { name: msp-max-alerter-data }

services:
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: msp-prometheus
    restart: unless-stopped
    user: "65534:65534"
    networks: [monitoring, msp_default]
    volumes:
      - prometheus_data:/prometheus
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/rules:/etc/prometheus/rules:ro
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=30d
      - --storage.tsdb.retention.size=4GB
      - --storage.tsdb.wal-compression
      - --web.enable-lifecycle
      - --web.external-url=http://127.0.0.1:9090
    ports: ["127.0.0.1:9090:9090"]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits: { memory: 1G }
        reservations: { memory: 256M }
    logging: &logging
      driver: json-file
      options: { max-size: "10m", max-file: "3" }

  alertmanager:
    image: prom/alertmanager:v0.34.1
    container_name: msp-alertmanager
    restart: unless-stopped
    environment:
      SMTP_AUTH_USER: "${SMTP_AUTH_USER:-}"
      ALERTMANAGER_WEBHOOK_TOKEN: "${ALERTMANAGER_WEBHOOK_TOKEN:?ALERTMANAGER_WEBHOOK_TOKEN обязателен}"
    volumes:
      - alertmanager_data:/alertmanager
      - ./alertmanager/alertmanager.yml.tmpl:/etc/alertmanager/alertmanager.yml.tmpl:ro
      - ./alertmanager/templates:/etc/alertmanager/templates:ro
      - ./alertmanager/entrypoint.sh:/etc/alertmanager/entrypoint.sh:ro
    entrypoint: ["/etc/alertmanager/entrypoint.sh"]
    command:
      - --config.file=/etc/alertmanager/alertmanager.yml
      - --storage.path=/alertmanager
      - --web.external-url=http://127.0.0.1:9093
      - --cluster.listen-address=
    ports: ["127.0.0.1:9093:9093"]
    networks: [monitoring, msp_default]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:9093/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits: { memory: 256M }
        reservations: { memory: 64M }
    logging: *logging

  grafana:
    image: grafana/grafana:10.4.2
    container_name: msp-grafana
    restart: unless-stopped
    env_file: .env
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/grafana.ini:/etc/grafana/grafana.ini:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
      - ./grafana/theme:/usr/share/grafana/public/build/mspshield:ro
    environment:
      GF_SECURITY_ADMIN_USER: "${GRAFANA_ADMIN_USER:-admin}"
      GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_ADMIN_PASSWORD:?GRAFANA_ADMIN_PASSWORD обязателен}"
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_AUTH_ANONYMOUS_ENABLED: "false"
      GF_SERVER_ROOT_URL: http://127.0.0.1:3000
      GF_ANALYTICS_REPORTING_ENABLED: "false"
      GF_UNIFIED_ALERTING_ENABLED: "false"
      GF_ALERTING_ENABLED: "false"
      GF_DEFAULT_THEME: light
      GF_USERS_DEFAULT_LANGUAGE: ru-RU
      GF_LOG_LEVEL: warn
    ports: ["127.0.0.1:3000:3000"]
    networks: [monitoring, msp_default]
    depends_on:
      prometheus: { condition: service_healthy }
    deploy:
      resources:
        limits: { memory: 512M }
        reservations: { memory: 128M }
    logging: *logging

  node-exporter:
    image: prom/node-exporter:v1.7.0
    container_name: msp-node-exporter
    restart: unless-stopped
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
      - /var/lib/node_exporter/textfile_collector:/var/lib/node_exporter/textfile_collector:ro
    command:
      - --path.procfs=/host/proc
      - --path.sysfs=/host/sys
      - --path.rootfs=/rootfs
      - --collector.textfile.directory=/var/lib/node_exporter/textfile_collector
      - --collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)
      - --no-collector.ipvs
    networks: [monitoring]

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.51.0
    container_name: msp-cadvisor
    restart: unless-stopped
    privileged: true
    devices: [/dev/kmsg:/dev/kmsg]
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/rootfs/var/lib/docker:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /dev/disk:/dev/disk:ro
    command: ["--housekeeping_interval=30s", "--docker_only=true", "--disable_metrics=percpu,sched,tcp,udp"]
    networks: [monitoring]

  blackbox-exporter:
    image: prom/blackbox-exporter:v0.24.0
    container_name: msp-blackbox
    restart: unless-stopped
    volumes: ["./prometheus/blackbox.yml:/etc/blackbox_exporter/config.yml:ro"]
    command: ["--config.file=/etc/blackbox_exporter/config.yml"]
    ports: ["127.0.0.1:9115:9115"]
    networks: [monitoring, msp_default]

  # Канонический MAX-контур: Alertmanager webhook → ручная pymax session.
  max-alerter:
    build: ../../../services/max_alerter
    container_name: msp-max-alerter
    restart: unless-stopped
    volumes:
      - ./max-session:/session
      - max-alerter-data:/data
    environment:
      MAX_PHONE: "${MAX_PHONE:?MAX_PHONE обязателен}"
      MAX_SESSION_DIR: /session
      MAX_SESSION_NAME: max.db
      MAX_SMS_CODE: "${MAX_SMS_CODE:-}"
      MAX_PASSWORD: "${MAX_PASSWORD:-}"
      MAX_CHAT_ID: "${MAX_CHAT_ID:?MAX_CHAT_ID обязателен}"
      WEBHOOK_TOKEN: "${ALERTMANAGER_WEBHOOK_TOKEN:?ALERTMANAGER_WEBHOOK_TOKEN обязателен}"
      TG_BOT_TOKEN: "${TELEGRAM_BOT_TOKEN:-}"
      TG_CHAT_ID: "${TELEGRAM_CHAT_ID:-}"
      SMTP_HOST: "${SMTP_HOST:-}"
      SMTP_PORT: "${SMTP_PORT:-465}"
      SMTP_USER: "${SMTP_USER:-}"
      SMTP_PASSWORD: "${SMTP_PASSWORD:-}"
      SMTP_FROM: "${SMTP_FROM:-}"
      ALERT_EMAIL_TO: "${ALERT_EMAIL_TO:-}"
      MAX_FAILURE_COOLDOWN: "${MAX_FAILURE_COOLDOWN:-300}"
    ports: ["127.0.0.1:9095:9095"]
    networks: [monitoring]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9095/health', timeout=3)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    deploy:
      resources:
        limits: { memory: 128M }
        reservations: { memory: 32M }
    logging: *logging

```

## Материал проекта: `deploy/yandex/monitoring/alertmanager/alertmanager.yml.tmpl`

<!-- SOURCE deploy/yandex/monitoring/alertmanager/alertmanager.yml.tmpl 13dbdbc6f79f7704 -->

```text
global:
  resolve_timeout: 5m
  smtp_smarthost: "postbox.cloud.yandex.net:465"
  smtp_from: "MSPShield <alert@msp-claude.online>"
  smtp_hello: "msp-claude.online"
  smtp_auth_username: "${SMTP_AUTH_USER}"
  smtp_auth_password: "${SMTP_AUTH_PASSWORD}"
  smtp_require_tls: true

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'severity', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: email-alert
  routes:
    # P1 идёт напрямую в канонический MAX userbot webhook и параллельно в email.
    - matchers: ['severity = P1']
      receiver: max-alert
      group_wait: 10s
      group_interval: 2m
      repeat_interval: 1h
      continue: true
    - matchers: ['severity = P1']
      receiver: email-alert
      group_wait: 10s
      group_interval: 2m
      repeat_interval: 1h
    - matchers: ['severity =~ "P2|P3"']
      receiver: email-alert
      group_wait: 1m
      group_interval: 10m
      repeat_interval: 4h

receivers:
  - name: max-alert
    webhook_configs:
      - url: 'http://msp-max-alerter:9095/alert'
        send_resolved: true
        http_config:
          authorization:
            type: Bearer
            credentials: '${ALERTMANAGER_WEBHOOK_TOKEN}'
  - name: email-alert
    email_configs:
      - to: "alert@msp-claude.online"
        send_resolved: true
        html: '{{ template "mspshield.alert.html" . }}'
        text: '{{ template "mspshield.alert.text" . }}'
        headers:
          Subject: '{{ template "mspshield.subject" . }}'
          Auto-Submitted: auto-generated
          Precedence: bulk

inhibit_rules:
  - source_matchers: ['severity = P1']
    target_matchers: ['severity =~ "P2|P3"']
    equal: ['alertname', 'instance']

```

## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
