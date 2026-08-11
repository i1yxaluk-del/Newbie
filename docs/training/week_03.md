# Week 3 · Monitoring (Prometheus + Grafana + Alerting)

## Цель

Уметь развернуть мониторинг с нуля на VM клиента, строить Grafana-дашборды
по GOLD signals, писать alert-правила и понимать как едет весь пайплайн
от метрики до email-уведомления.

---

## 1. Архитектура мониторинга MSPShield

```
┌─── VM клиента ───────────────────────────────────────────────┐
│                                                                │
│  node-exporter:9100   ← CPU, RAM, disk, network              │
│  cAdvisor:8080        ← Docker контейнеры                     │
│  blackbox-exporter    ← HTTP/SMTP/TCP пробы                   │
│  restic textfile      ← бэкап-метрики (.prom файлы)          │
│                                                                │
│  ┌── Prometheus :9090 ──────────────────────────────────────┐  │
│  │  scrape → хранит 30д → eval rules → Alertmanager :9093   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌── Alertmanager ─────────────────────────────────────────┐   │
│  │  P1/P2/P3 routing → email (Stalwart :25)               │   │
│  │                     → webhook (backend → MAX/Telegram)  │   │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Grafana :3000 ← dashboards, datasource=Prometheus            │
│  Доступ: https://mon.<domain> через Caddy reverse proxy       │
└────────────────────────────────────────────────────────────────┘
```

**Ключевой момент:** мониторинг-стек работает в **отдельной Docker-сети**
(`msp-monitoring`, 172.20.0.0/24). Это изоляция — если клиентский контейнер
упадёт, мониторинг продолжит работать. Но значит SMTP/email нужно
думать отдельно (см. §5 ниже).

---

## 2. Развёртывание мониторинга с нуля (команды)

### 2.1. Создаём сеть и директории

```bash
# На VM клиента
sudo mkdir -p /opt/msp/Newbie/deploy/yandex/monitoring/{prometheus/rules,alertmanager/templates,grafana/{dashboards,provisioning/{datasources,dashboards},theme}}
sudo chown -R ubuntu:ubuntu /opt/msp/Newbie/deploy/yandex/monitoring
```

### 2.2. Копируем конфиги из репозитория

```bash
# С Windows-станции (через VPN)
scp -r deploy/yandex/monitoring/* ubuntu@<IP>:/opt/msp/Newbie/deploy/yandex/monitoring/
```

Или с VM если репо уже там:
```bash
cd /opt/msp/Newbie
cp -r deploy/yandex/monitoring/* /opt/msp/Newbie/deploy/yandex/monitoring/
```

### 2.3. Создаём .env с паролями

```bash
cat > /opt/msp/Newbie/deploy/yandex/monitoring/.env << 'EOF'
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<сгенерируй 24+ символа>
EOF
sudo chmod 600 /opt/msp/Newbie/deploy/yandex/monitoring/.env
```

### 2.4. Запускаем стек

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
docker compose up -d

# Проверяем что всё поднялось
docker compose ps
```

Ожидаемый вывод:
```
NAME               STATUS
msp-prometheus     Up (healthy)
msp-grafana        Up
msp-alertmanager   Up (healthy)
msp-node-exporter  Up
msp-cadvisor       Up
msp-blackbox       Up
```

### 2.5. Подключаем external сеть (чтобы Alertmanager и Blackbox
###     видели клиентские сервисы)

```bash
# Создаём сеть msp_default если её нет (создаётся app-stack'ом)
docker network create msp_default 2>/dev/null || true

# Alertmanager и Blackbox уже подключены к обеим сетям в compose:
#   networks: [monitoring, msp_default]
```

### 2.6. Проверяем Prometheus scrape targets

```bash
# SSH-туннель (пока нет Caddy proxy)
ssh -L 9090:127.0.0.1:9090 ubuntu@<IP>

# Браузер → http://localhost:9090/targets
# Все таргеты должны быть UP
```

### 2.7. Проверяем метрики

```bash
# На VM
curl -s http://127.0.0.1:9090/api/v1/query?query=up | python3 -m json.tool
# Ожидаем: все таргеты со value "1"
```

---

## 3. GOLD Signals — как строить дашборды

**GOLD** (Google's Four Golden Signals) — минимальный набор метрик,
который должен быть на каждом сервисе:

| Signal | Что измеряет | PromQL пример | Порог алёрта |
|--------|-------------|---------------|-------------|
| **Latency** | Время ответа | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` | P99 > 5s |
| **Traffic** | RPS, запросы/сек | `rate(http_requests_total[5m])` | RPS = 0 (сервис умер) |
| **Errors** | % ошибок | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])` | > 0.5% |
| **Saturation** | Нагрузка ресурсов | `container_memory_working_set_bytes / container_spec_memory_limit_bytes` | > 90% |

### 3.1. Дашборд для клиентского сервиса (шаблон)

Для каждого сервиса клиента (1С, веб-сайт, API) строим по GOLD:

```
┌─────────────────────────────────────────────────────────────┐
│  Row: <Service Name>                                        │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│ Latency  │ Traffic  │ Errors   │ Saturat. │ Status        │
│ P99=1.2s │ 42 rps   │ 0.1%     │ RAM 67%  │ ● UP          │
│ [graph]  │ [graph]  │ [graph]  │ [graph]  │               │
├──────────┴──────────┴──────────┴──────────┴────────────────┤
│  Details: CPU per core, Disk I/O, Network bytes             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2. Строим дашборд в Grafana: пошагово

1. **Открываем** `https://mon.<domain>` (или через SSH-туннель `localhost:3000`)
2. **Datasource** — должен быть уже провижен (uid `prometheus`). Проверяем:
   - Configuration → Data Sources → Prometheus → Save & Test → "Data source is working"
3. **Новый дашборд:** Dashboards → New → New Dashboard → Add query

**Panel 1 — Latency (Stat panel):**
```promql
# Для HTTP-сервиса:
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Если нет histogram — используем blackbox probe:
probe_duration_seconds{job="blackbox-http"}
```
- Visualization: Stat
- Unit: `s`
- Thresholds: green < 1, amber 1-5, red > 5

**Panel 2 — Traffic (Time series):**
```promql
rate(http_requests_total[5m])
# Или для сайта — blackbox:
probe_success{job="blackbox-http"}
```
- Visualization: Time series
- Legend: `{{instance}}`

**Panel 3 — Errors (Stat panel):**
```promql
# HTTP 5xx rate:
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Или probe failures:
1 - probe_success
```
- Visualization: Stat
- Unit: `percentunit`
- Thresholds: green < 0.005, amber 0.005-0.05, red > 0.05

**Panel 4 — Saturation (Gauge):**
```promql
# RAM saturation:
container_memory_working_set_bytes{name=~"<service>"} / container_spec_memory_limit_bytes{name=~"<service>"}

# CPU saturation:
rate(container_cpu_usage_seconds_total{name=~="<service>"}[5m])
```
- Visualization: Gauge
- Min: 0, Max: 1
- Thresholds: green < 0.7, amber 0.7-0.9, red > 0.9

**Panel 5 — VM Resources (Row + Time series):**
```promql
# CPU per core:
100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)

# RAM:
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# Disk:
(node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100
```

### 3.3. Сохраняем дашборд как JSON

После настройки: Dashboard settings → JSON Model → скопировать →
сохранить в `deploy/yandex/monitoring/grafana/dashboards/<name>.json`.

Это важно: **дашборды провижатся из JSON файлов** при рестарте Grafana.
Ручные изменения в UI затрутся при следующем `docker compose up -d`
если JSON не обновлён.

---

## 4. Alert-правила: пишем и тестируем

### 4.1. Структура правила

```yaml
# deploy/yandex/monitoring/prometheus/rules/<category>.yml
groups:
  - name: <category>
    rules:
      - alert: <AlertName>          # CamelCase, уникальное
        expr: <promql_expression>    # когда True → alert firing
        for: <duration>              # сколько ждать перед firing
        labels:
          severity: P1|P2|P3        # приоритет
        annotations:
          summary: "человекочитаемое описание"
          host: "node-01.<domain>"   # для email-шаблона
          metric: 'выражение = {{ $value }}'  # текущее значение
          runbook: "https://github.com/<org>/<repo>/blob/main/deploy/yandex/monitoring/runbooks/R-<id>.md"
```

### 4.2. Severity классификация

| Severity | Описание | group_wait | repeat | Пример |
|----------|----------|------------|--------|--------|
| **P1** | Полный простой | 10s | 1h | SiteDown, NodeDown, BackupFailed |
| **P2** | Деградация | 1m | 4h | HighCPU, LowDisk, ContainerRestartLoop |
| **P3** | Информационный | 1m | 4h | SiteSlowResponse, BackupInProgress |

P1 ингибирует P2/P3 с тем же alertname — чтобы не спамить
когда уже есть критический алёрт.

### 4.3. Практика: написать правило

Создай файл `rules/myservice.yml`:

```yaml
groups:
  - name: myservice
    rules:
      - alert: MyServiceDown
        expr: up{job="myservice"} == 0
        for: 2m
        labels:
          severity: P1
        annotations:
          summary: "myservice · сервис недоступен более 2 мин"
          host: "node-01.client-domain"
          metric: 'up = 0'
          runbook: "https://github.com/i1yxaluk-del/Newbie/blob/main/deploy/yandex/monitoring/runbooks/R-node-down.md"
```

Применяем:
```bash
# Копируем на VM
scp rules/myservice.yml ubuntu@<IP>:/opt/msp/Newbie/deploy/yandex/monitoring/prometheus/rules/

# Reload Prometheus (без рестарта!)
ssh ubuntu@<IP> "docker kill --signal=SIGHUP msp-prometheus"

# Проверяем в UI: http://localhost:9090/alerts
```

### 4.4. Тест alert без реального сбоя

Отправляем тестовый alert через API:
```bash
# На VM
python3 -c "
import urllib.request, json, time
t = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
alerts = [{'labels':{'alertname':'TestAlert','severity':'P1','instance':'test'},
           'annotations':{'summary':'test alert','host':'node-01','metric':'test=1',
           'runbook':'https://github.com/i1yxaluk-del/Newbie'},
           'startsAt':t}]
data = json.dumps(alerts).encode()
req = urllib.request.Request('http://127.0.0.1:9093/api/v2/alerts',
    data=data, headers={'Content-Type':'application/json'})
urllib.request.urlopen(req)
print('Alert sent')
"
```

Проверяем:
```bash
# Alertmanager status
curl -s http://127.0.0.1:9093/api/v2/alerts | python3 -m json.tool

# Email delivery metrics
curl -s http://127.0.0.1:9093/metrics | grep alertmanager_notifications
```

---

## 5. Alertmanager email: почему не через Postbox напрямую

**Проблема:** Alertmanager v0.27 встроенный SMTP client не поддерживает
implicit TLS. Postbox работает только на :465 implicit TLS.

**Решение:** Alertmanager подключён к обеим сетям (`msp-monitoring` +
`msp_default`) и отправляет email через Stalwart `:25` без TLS:

```yaml
# alertmanager.yml
global:
  smtp_smarthost: "stalwart:25"
  smtp_from: "alert@msp-claude.online"
  smtp_hello: "msp-claude.online"     # ← Обязательно! Иначе Stalwart
                                       #   отклонит container hostname
  smtp_require_tls: false
```

**Anti-spam:** email содержит и HTML и text/plain части + заголовки
`List-ID`, `X-Mailer`, `X-Priority` — без этого Gmail/Outlook кладёт
в spam.

---

## 6. Restic бэкап-метрики

Restic не отдаёт метрики. Мы используем **node-exporter textfile collector**:

```
restic backup → /opt/restic-scripts/backup.sh
  → пишет /var/lib/node_exporter/textfile_collector/restic_backup.prom
  → node-exporter с --collector.textfile.directory подхватывает
  → Prometheus скрейпит node-exporter
  → Grafana dashboard "MSPShield — Backups"
```

### 6.1. Настройка textfile collector

В `docker-compose.yml` node-exporter:
```yaml
node-exporter:
  volumes:
    - /var/lib/node_exporter/textfile_collector:/var/lib/node_exporter/textfile_collector:ro
  command:
    - "--collector.textfile.directory=/var/lib/node_exporter/textfile_collector"
```

### 6.2. Метрики в .prom файле

```prometheus
# HELP restic_backup_success Last restic backup result (1=ok, 0=fail, 2=in-progress)
# TYPE restic_backup_success gauge
restic_backup_success{host="node-01",repo="mspshield-prod"} 1
restic_backup_timestamp_seconds{host="node-01",repo="mspshield-prod"} 1780497102
restic_backup_size_bytes{host="node-01",repo="mspshield-prod"} 191461026
```

### 6.3. Alert-правила для бэкапов

| Alert | Expression | Severity |
|-------|-----------|----------|
| BackupFailed | `restic_backup_success == 0` | P1 |
| BackupMissed24h | `time() - restic_backup_timestamp_seconds > 93600` | P1 |
| BackupSizeDropped | `size < avg_over_time(size[7d]) * 0.5` | P2 |
| BackupInProgress | `restic_backup_success == 2 for 30m` | P3 |

---

## 7. Grafana доступ через DNS (как Vaultwarden)

Grafana доступна по `https://mon.<domain>` без SSH-туннеля.

**Как настроить:**

1. DNS A-запись: `mon.<domain>` → `<IP>` (у регистратора)
2. Caddy block в `/etc/caddy/Caddyfile`:
```
mon.msp-claude.online {
    encode gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        -Server
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
```
3. `sudo systemctl reload caddy` — Caddy получит SSL-сертификат автоматически

---

## 8. Уроки реального деплоя (monitoring-specific)

### 8.1. node-exporter textfile — метрики не видны Prometheus

**Симптом:** `.prom` файл существует, но метрик нет в Prometheus.

**Причина:** node-exporter запущен без `--collector.textfile.directory`
и без volume mount.

**Фикс:** добавить флаг + mount (см. §6.1 выше).

### 8.2. status-history → "Data does not have a time field"

**Симптом:** Grafana panel типа `status-history` показывает ошибку.

**Причина:** `status-history` требует range data с time-полем.
Gauge-метрики с подзапросами возвращают instant vector без time.

**Фикс:** использовать `state-timeline` тип панели вместо `status-history`.

### 8.3. Alertmanager email в spam

**Причина:** HTML-only email без text/plain альтернативы.

**Фикс:** добавить `text:` template в email_configs + заголовки
`List-ID`, `X-Mailer`, `X-Priority`.

### 8.4. Alertmanager SMTP EHLO rejected

**Причина:** Container hostname ( типа `a1b2c3d4e5f6`) не резолвится.

**Фикс:** `smtp_hello: "msp-claude.online"` — Stalwart принимает
только FQDN в EHLO.

### 8.5. Restic stale lock

**Симптом:** `restic forget` или `restic backup` падает с
"repository is already locked by PID... lock was created at ... ago".

**Фикс:** `sudo bash -c 'source /etc/restic/env.sh && restic unlock'`

---

## Задачи (практика)

- [ ] Развернуть мониторинг-стек на test-VM от нуля (§2)
- [ ] Построить GOLD signals дашборд для тестового сервиса (§3)
- [ ] Написать 2 alert-правила и протестировать через API (§4)
- [ ] Настроить restic textfile collector и проверить метрики (§6)
- [ ] Настроить `mon.<domain>` через Caddy (§7)
- [ ] Прочитать все runbooks в `deploy/yandex/monitoring/runbooks/`
- [ ] Разобрать 3 последних alert'а в истории, что с ними делали
- [ ] ⚠️ Прочитать `deploy/yandex/README.md` §10.M про архитектуру
      мониторинга и §10.0.12–10.0.16 про уроки деплоя

## Production задачи

- [ ] Взять любой non-critical alert (HighCPU / LowDisk в off-hours),
      отреагировать самостоятельно, написать write-up
- [ ] Настроить новый alert для клиентского сервиса

## Read

- Prometheus: "First steps" + "Querying basics"
- [PromLabs promql-tutorial](https://promlabs.com/promql-cheat-sheet/) 30 мин
- [GOLD Signals](https://sre.google/sre-book/monitoring-distributed-systems/) — Google SRE Chapter 6
- `deploy/yandex/README.md` §10.M — наша архитектура мониторинга

## Check-in

1. Различие `rate()` vs `irate()` vs `increase()`?
2. Как устроен Alertmanager routing (P1/P2/P3)?
3. Зачем `for: 10m` в правиле alert'а?
4. 4 GOLD signals — назови и дай пример PromQL для каждого
5. Почему Alertmanager шлёт email через Stalwart :25, а не Postbox :465?
6. Как работает node-exporter textfile collector?
7. Почему `state-timeline`, а не `status-history` для gauge-метрик?

## DoD

- Развёрнут мониторинг-стек на test-VM
- Построен GOLD signals дашборд (по скриншоту show-and-tell)
- Отреагировал на 1+ реальный alert самостоятельно
- Добавил 2+ новых alert-правила
