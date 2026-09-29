# Обучение Junior и безопасная передача работы

Допуск выдаётся по доказанному навыку, а не по числу недель. L0 наблюдает, L1 действует при совместном экране, L2 выполняет одобренное изменение с reviewer, L3 самостоятельно ведёт ограниченные Bronze P2/P3.

Навык проверяется полным циклом: прочитать скрипт, назвать входы и побочные эффекты, выполнить на стенде, проверить результат, сделать откат и оформить evidence. Провал security-критерия означает повтор.

Передача владельца новому администратору уменьшает bus factor только тогда, когда второй человек реально восстанавливал систему, переносил MAX session и диагностировал почтовую ошибку.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

## Материал проекта: `docs/training/README.md`

<!-- SOURCE docs/training/README.md 771e946bba0ed21f -->

## Программа допуска Junior MSP Engineer

Допуск основан на evidence, а не на сроке работы.

### Уровни

| Уровень | Разрешено | Запрещено |
|---|---|---|
| L0 Observe | dashboards, read-only logs, документация | изменения |
| L1 Assisted | runbook при screen sharing | самостоятельный production |
| L2 Supervised | одобренный change с reviewer | firewall/backup policy/P1 commander |
| L3 Independent | Bronze P2/P3 и регулярные операции | Gold/on-call без отдельного gate |

### Маршрут

1. [`JUNIOR_OPERATIONS_GUIDE.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/training/JUNIOR_OPERATIONS_GUIDE.md) — как читать scripts/runbooks.
2. `week_01.md`…`week_12.md` — теория и базовая практика.
3. [`DEPLOYMENT_MIGRATION_LABS.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/training/DEPLOYMENT_MIGRATION_LABS.md) — реальные уроки deployment.
4. [`../runbooks/README.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/README.md) — incident response.
5. Итоговый Bronze exam.

### Обязательные навыки L2

- preflight и чтение Compose config без вывода секретов;
- backup Mongo и stateful services с корректным writer handling;
- clean-room restore и RTO/RPO evidence;
- MAX session transfer без автоматической SMS;
- диагностика Postbox SMTP 535;
- TCP/443 VM health вместо вывода по одному ICMP;
- SSH host-key verification;
- change/rollback/client update.

Провал security-критерия означает повтор упражнения.


## Материал проекта: `docs/training/JUNIOR_OPERATIONS_GUIDE.md`

<!-- SOURCE docs/training/JUNIOR_OPERATIONS_GUIDE.md 3ffffe67a676a074 -->

## Памятка Junior: как читать скрипты и runbook

### Перед запуском shell/Python/PowerShell

- Прочитай комментарий в начале файла: назначение, входы, побочные эффекты, rollback.
- Найди команды удаления, перезапуска, firewall и изменения прав.
- Убедись, что переменные не пустые и относятся к нужному tenant.
- Запусти режим проверки (`--dry-run`, `--check`, `set -n`) если он доступен.
- Не вставляй токены в командную строку: они попадут в history/process list.

### Обязательные русские комментарии для нового скрипта

```text
Назначение: какую проблему решает скрипт.
Где запускать: workstation / bastion / monitoring / client host.
Входные параметры: что обязательно и пример безопасного значения.
Побочные эффекты: какие файлы, сервисы или правила меняются.
Проверка успеха: команда и ожидаемый результат.
Откат: как вернуть состояние.
```

Комментарии должны объяснять «почему», а не повторять синтаксис команды. Секреты и реальные клиентские значения в примеры не добавляются.

### Стоп-условия

Остановись и эскалируй, если не совпадает hostname, нет backup/rollback, команда затрагивает несколько tenants, получен неожиданный вывод, операция касается ПДн вне подписанного периметра или требуется действие вне твоего допуска.


## Материал проекта: `docs/training/DEPLOYMENT_MIGRATION_LABS.md`

<!-- SOURCE docs/training/DEPLOYMENT_MIGRATION_LABS.md 594ab0dadf860247 -->

## Практикум Junior: deployment, backup и migration

Все упражнения выполняются на стенде без production-секретов и ПДн.

| Lab | Сценарий | Успех | Критический провал |
|---|---|---|---|
| 1 | `.env` с BOM/CRLF и пустым ADMIN_TOKEN | preflight находит обе проблемы, Junior объясняет риск | просто удаляет файл или печатает секреты |
| 2 | Alertmanager с отсутствующим SMTP password | Compose/entrypoint fail-fast, после фикса тестовое письмо доставлено | отключает auth/TLS |
| 3 | backup Mongo + Vaultwarden + Stalwart | создаёт staging archives и восстанавливает в clean VM | копирует live Mongo volume |
| 4 | перенос MAX session | session check проходит без `--authorize` | запускает SMS автоматически |
| 5 | VM watcher при закрытом ICMP | TCP/443 различает stopped и network failure | использует только ping или hardcoded VM ID |
| 6 | смена SSH host key | сверяет fingerprint в console и обновляет known_hosts | `StrictHostKeyChecking=no` |
| 7 | полный tenant onboarding | scope → change → alert → restore → report | начинает без договора/окна/rollback |
| 8 | Миграция на чистую ВМ по `MIGRATION_RUNBOOK` §9 (симуляция) | тома восстановлены (du ≈ бэкап), Stalwart не в bootstrap, сайт 200 | молчаливые пустые тома; bootstrap-режим; Caddy-заглушка |

### Evidence каждого lab

- дата, стенд и версия commit;
- команды без секретов;
- ожидаемый и фактический результат;
- screenshot/log fragment;
- rollback и его результат;
- вывод наставника: pass/repeat.

### Разбор кейсов миграции 28.09 (перед Lab 8)

Прочитать [`../deployment/MIGRATION_RUNBOOK.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/MIGRATION_RUNBOOK.md) §9 и разобрать с Junior'ом:

1. Почему «сайт не работает» не всегда вина сайта? (доступность IP из сети/региона, §9.2)
2. Чем опасен `sudo cp root-only/*.tar.gz`? (glob раскрывается до sudo, §9.4)
3. Почему Stalwart без томов уходит в bootstrap и что это значит для почты? (§9.4)
4. Что пересоздаётся при переезде в новый аккаунт? (ключ+DKIM Postbox, ключ+init restic, §9.5–9.6)
5. Какие два gate добавились перед DNS switch? (TCP из региона; отсутствие bootstrap, §9.8)

Эталонные формулировки — в §9.2–§9.8.

Доступ L2 выдаётся только после Labs 1–6 и общего Bronze-сценария.


## Материал проекта: `docs/training/week_01.md`

<!-- SOURCE docs/training/week_01.md 4e8fce73d98d5fc2 -->

## Week 1 · Онбординг + tooling

### Цель недели

Доступы выданы, tooling настроен, первый P3 закрыт в паре.

### День 1

- [ ] Подписание NDA.
- [ ] Установка: Vaultwarden, WireGuard, VSCode, terminal (Alacritty/iTerm).
- [ ] Создание аккаунтов: Kaiten, GitHub org, Telegram, Vaultwarden, Grafana read-only.
- [ ] Welcome-звонок 30 минут с owner: expectations, контакты, «как просить помощь».
- [ ] Краткий обзор `README.md`, `docs/burnout_guard.md`.

### День 2-3

- [ ] Прочитать: `README.md`, `docs/runbooks/README.md`, `docs/checklists/weekly.md`.
- [ ] Bluebook: написать своё резюме всех инструментов и команд, с которыми раньше работал.
- [ ] Пройти pairing-сессию: owner показывает, как берётся тикет в Kaiten, как ведётся P3.
- [ ] Смотреть, как owner отвечает клиенту в Telegram (тон, структура).

### День 4-5

- [ ] Взять первый P3 в паре (password reset — R-09).
- [ ] Выполнить под supervision (owner поправляет в реальном времени).
- [ ] Написать свой first post-mortem-style write-up в Kaiten (5-7 строк: что делал, что узнал).

### Check-in пятницы (15 мин)

Вопросы от owner:
1. Что из инструментов новое для тебя? Что задалось сложно?
2. Что тебе непонятно в процессе пока?
3. Что удобно / неудобно?

### Итог недели

- Все доступы получены, Vaultwarden настроен, 2FA включена.
- Закрыт 1+ P3 в паре.
- Прочитал все обязательные документы.
- Написал bluebook своего skill-профиля.


## Материал проекта: `docs/training/week_02.md`

<!-- SOURCE docs/training/week_02.md 6ff77890614a3099 -->

## Week 2 · Linux deep-dive + наш baseline

### Цель

Понимать наш production baseline (Ubuntu 22.04 + конкретные роли).
Уметь провести первичную диагностику без помощи.

### Задачи

- [ ] Прочитать `technical/0_Common/ansible/playbooks/site.yml` и
      explain back: что делают какие роли.
- [ ] Развернуть локальную копию baseline в VM (Vagrant / VirtualBox),
      запустить playbook вручную.
- [ ] Сессия с owner: 1 час про systemd, 1 час про networking в Linux.
- [ ] ⚠️ **Урок из деплоя:** На test-VM после установки Docker проверить
      `docker info --format '{{.Driver}}'`. Если `overlayfs` (Docker 29+ на
      Ubuntu 22.04) — нужно создать `/etc/docker/daemon.json` с
      `{"storage-driver": "overlay2"}` и рестартить Docker. Иначе cAdvisor
      не видит контейнеры. См. `deploy/yandex/README.md` §10.0.1.
- [ ] Пройти checklist из R-06 (disk space critical) на своей VM:
      создать проблему, решить по runbook'у.

### Задачи на production (под supervision)

- [ ] Провести patch-проверку одного Bronze-клиента (`patch_nondisruptive.yml`
      в dry-run, затем apply).
- [ ] Закрыть 2-3 P3 тикета (password reset, add user, disk cleanup).

### Read

- `man systemd.service` (обзорно).
- `man journalctl` (разбор примеров).
- Briefly: Ubuntu release notes 22.04.

### Check-in

1. Можешь объяснить словами, чем `sshd` отличается от `systemd-sshd@`
   (обслуживающих).
2. Что делает `journalctl --vacuum-time=7d`?
3. Зачем `sudo systemctl daemon-reload` после правки unit-файла?

### DoD

- Baseline playbook разворачивается локально из твоих рук.
- Закрыл 2 P3 самостоятельно (без pairing).
- Обновил свой bluebook.


## Материал проекта: `docs/training/week_03.md`

<!-- SOURCE docs/training/week_03.md 4e9a36876d9a8d53 -->

## Week 3 · Monitoring (Prometheus + Grafana + Alerting)

### Цель

Уметь развернуть мониторинг с нуля на VM клиента, строить Grafana-дашборды
по GOLD signals, писать alert-правила и понимать как едет весь пайплайн
от метрики до email-уведомления.

---

### 1. Архитектура мониторинга MSPShield

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

### 2. Развёртывание мониторинга с нуля (команды)

#### 2.1. Создаём сеть и директории

```bash
## На VM клиента
sudo mkdir -p /opt/msp/Newbie/deploy/yandex/monitoring/{prometheus/rules,alertmanager/templates,grafana/{dashboards,provisioning/{datasources,dashboards},theme}}
sudo chown -R ubuntu:ubuntu /opt/msp/Newbie/deploy/yandex/monitoring
```

#### 2.2. Копируем конфиги из репозитория

```bash
## С Windows-станции (через VPN)
scp -r deploy/yandex/monitoring/* ubuntu@<IP>:/opt/msp/Newbie/deploy/yandex/monitoring/
```

Или с VM если репо уже там:
```bash
cd /opt/msp/Newbie
cp -r deploy/yandex/monitoring/* /opt/msp/Newbie/deploy/yandex/monitoring/
```

#### 2.3. Создаём .env с паролями

```bash
cat > /opt/msp/Newbie/deploy/yandex/monitoring/.env << 'EOF'
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<сгенерируй 24+ символа>
EOF
sudo chmod 600 /opt/msp/Newbie/deploy/yandex/monitoring/.env
```

#### 2.4. Запускаем стек

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
docker compose up -d

## Проверяем что всё поднялось
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

#### 2.5. Подключаем external сеть (чтобы Alertmanager и Blackbox
####     видели клиентские сервисы)

```bash
## Создаём сеть msp_default если её нет (создаётся app-stack'ом)
docker network create msp_default 2>/dev/null || true

## Alertmanager и Blackbox уже подключены к обеим сетям в compose:
##   networks: [monitoring, msp_default]
```

#### 2.6. Проверяем Prometheus scrape targets

```bash
## SSH-туннель (пока нет Caddy proxy)
ssh -L 9090:127.0.0.1:9090 ubuntu@<IP>

## Браузер → http://localhost:9090/targets
## Все таргеты должны быть UP
```

#### 2.7. Проверяем метрики

```bash
## На VM
curl -s http://127.0.0.1:9090/api/v1/query?query=up | python3 -m json.tool
## Ожидаем: все таргеты со value "1"
```

---

### 3. GOLD Signals — как строить дашборды

**GOLD** (Google's Four Golden Signals) — минимальный набор метрик,
который должен быть на каждом сервисе:

| Signal | Что измеряет | PromQL пример | Порог алёрта |
|--------|-------------|---------------|-------------|
| **Latency** | Время ответа | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` | P99 > 5s |
| **Traffic** | RPS, запросы/сек | `rate(http_requests_total[5m])` | RPS = 0 (сервис умер) |
| **Errors** | % ошибок | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])` | > 0.5% |
| **Saturation** | Нагрузка ресурсов | `container_memory_working_set_bytes / container_spec_memory_limit_bytes` | > 90% |

#### 3.1. Дашборд для клиентского сервиса (шаблон)

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

#### 3.2. Строим дашборд в Grafana: пошагово

1. **Открываем** `https://mon.<domain>` (или через SSH-туннель `localhost:3000`)
2. **Datasource** — должен быть уже провижен (uid `prometheus`). Проверяем:
   - Configuration → Data Sources → Prometheus → Save & Test → "Data source is working"
3. **Новый дашборд:** Dashboards → New → New Dashboard → Add query

**Panel 1 — Latency (Stat panel):**
```promql
## Для HTTP-сервиса:
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

## Если нет histogram — используем blackbox probe:
probe_duration_seconds{job="blackbox-http"}
```
- Visualization: Stat
- Unit: `s`
- Thresholds: green < 1, amber 1-5, red > 5

**Panel 2 — Traffic (Time series):**
```promql
rate(http_requests_total[5m])
## Или для сайта — blackbox:
probe_success{job="blackbox-http"}
```
- Visualization: Time series
- Legend: `{{instance}}`

**Panel 3 — Errors (Stat panel):**
```promql
## HTTP 5xx rate:
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

## Или probe failures:
1 - probe_success
```
- Visualization: Stat
- Unit: `percentunit`
- Thresholds: green < 0.005, amber 0.005-0.05, red > 0.05

**Panel 4 — Saturation (Gauge):**
```promql
## RAM saturation:
container_memory_working_set_bytes{name=~"<service>"} / container_spec_memory_limit_bytes{name=~"<service>"}

## CPU saturation:
rate(container_cpu_usage_seconds_total{name=~="<service>"}[5m])
```
- Visualization: Gauge
- Min: 0, Max: 1
- Thresholds: green < 0.7, amber 0.7-0.9, red > 0.9

**Panel 5 — VM Resources (Row + Time series):**
```promql
## CPU per core:
100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)

## RAM:
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

## Disk:
(node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100
```

#### 3.3. Сохраняем дашборд как JSON

После настройки: Dashboard settings → JSON Model → скопировать →
сохранить в `deploy/yandex/monitoring/grafana/dashboards/<name>.json`.

Это важно: **дашборды провижатся из JSON файлов** при рестарте Grafana.
Ручные изменения в UI затрутся при следующем `docker compose up -d`
если JSON не обновлён.

---

### 4. Alert-правила: пишем и тестируем

#### 4.1. Структура правила

```yaml
## deploy/yandex/monitoring/prometheus/rules/<category>.yml
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

#### 4.2. Severity классификация

| Severity | Описание | group_wait | repeat | Пример |
|----------|----------|------------|--------|--------|
| **P1** | Полный простой | 10s | 1h | SiteDown, NodeDown, BackupFailed |
| **P2** | Деградация | 1m | 4h | HighCPU, LowDisk, ContainerRestartLoop |
| **P3** | Информационный | 1m | 4h | SiteSlowResponse, BackupInProgress |

P1 ингибирует P2/P3 с тем же alertname — чтобы не спамить
когда уже есть критический алёрт.

#### 4.3. Практика: написать правило

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
## Копируем на VM
scp rules/myservice.yml ubuntu@<IP>:/opt/msp/Newbie/deploy/yandex/monitoring/prometheus/rules/

## Reload Prometheus (без рестарта!)
ssh ubuntu@<IP> "docker kill --signal=SIGHUP msp-prometheus"

## Проверяем в UI: http://localhost:9090/alerts
```

#### 4.4. Тест alert без реального сбоя

Отправляем тестовый alert через API:
```bash
## На VM
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
## Alertmanager status
curl -s http://127.0.0.1:9093/api/v2/alerts | python3 -m json.tool

## Email delivery metrics
curl -s http://127.0.0.1:9093/metrics | grep alertmanager_notifications
```

---

### 5. Alertmanager email: почему не через Postbox напрямую

**Проблема:** Alertmanager v0.27 встроенный SMTP client не поддерживает
implicit TLS. Postbox работает только на :465 implicit TLS.

**Решение:** Alertmanager подключён к обеим сетям (`msp-monitoring` +
`msp_default`) и отправляет email через Stalwart `:25` без TLS:

```yaml
## alertmanager.yml
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

### 6. Restic бэкап-метрики

Restic не отдаёт метрики. Мы используем **node-exporter textfile collector**:

```
restic backup → /opt/restic-scripts/backup.sh
  → пишет /var/lib/node_exporter/textfile_collector/restic_backup.prom
  → node-exporter с --collector.textfile.directory подхватывает
  → Prometheus скрейпит node-exporter
  → Grafana dashboard "MSPShield — Backups"
```

#### 6.1. Настройка textfile collector

В `docker-compose.yml` node-exporter:
```yaml
node-exporter:
  volumes:
    - /var/lib/node_exporter/textfile_collector:/var/lib/node_exporter/textfile_collector:ro
  command:
    - "--collector.textfile.directory=/var/lib/node_exporter/textfile_collector"
```

#### 6.2. Метрики в .prom файле

```prometheus
## HELP restic_backup_success Last restic backup result (1=ok, 0=fail, 2=in-progress)
## TYPE restic_backup_success gauge
restic_backup_success{host="node-01",repo="mspshield-prod"} 1
restic_backup_timestamp_seconds{host="node-01",repo="mspshield-prod"} 1780497102
restic_backup_size_bytes{host="node-01",repo="mspshield-prod"} 191461026
```

#### 6.3. Alert-правила для бэкапов

| Alert | Expression | Severity |
|-------|-----------|----------|
| BackupFailed | `restic_backup_success == 0` | P1 |
| BackupMissed24h | `time() - restic_backup_timestamp_seconds > 93600` | P1 |
| BackupSizeDropped | `size < avg_over_time(size[7d]) * 0.5` | P2 |
| BackupInProgress | `restic_backup_success == 2 for 30m` | P3 |

---

### 7. Grafana доступ через DNS (как Vaultwarden)

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

### 8. Уроки реального деплоя (monitoring-specific)

#### 8.1. node-exporter textfile — метрики не видны Prometheus

**Симптом:** `.prom` файл существует, но метрик нет в Prometheus.

**Причина:** node-exporter запущен без `--collector.textfile.directory`
и без volume mount.

**Фикс:** добавить флаг + mount (см. §6.1 выше).

#### 8.2. status-history → "Data does not have a time field"

**Симптом:** Grafana panel типа `status-history` показывает ошибку.

**Причина:** `status-history` требует range data с time-полем.
Gauge-метрики с подзапросами возвращают instant vector без time.

**Фикс:** использовать `state-timeline` тип панели вместо `status-history`.

#### 8.3. Alertmanager email в spam

**Причина:** HTML-only email без text/plain альтернативы.

**Фикс:** добавить `text:` template в email_configs + заголовки
`List-ID`, `X-Mailer`, `X-Priority`.

#### 8.4. Alertmanager SMTP EHLO rejected

**Причина:** Container hostname ( типа `a1b2c3d4e5f6`) не резолвится.

**Фикс:** `smtp_hello: "msp-claude.online"` — Stalwart принимает
только FQDN в EHLO.

#### 8.5. Restic stale lock

**Симптом:** `restic forget` или `restic backup` падает с
"repository is already locked by PID... lock was created at ... ago".

**Фикс:** `sudo bash -c 'source /etc/restic/env.sh && restic unlock'`

---

### Задачи (практика)

- [ ] Развернуть мониторинг-стек на test-VM от нуля (§2)
- [ ] Построить GOLD signals дашборд для тестового сервиса (§3)
- [ ] Написать 2 alert-правила и протестировать через API (§4)
- [ ] Настроить restic textfile collector и проверить метрики (§6)
- [ ] Настроить `mon.<domain>` через Caddy (§7)
- [ ] Прочитать все runbooks в `deploy/yandex/monitoring/runbooks/`
- [ ] Разобрать 3 последних alert'а в истории, что с ними делали
- [ ] ⚠️ Прочитать `deploy/yandex/README.md` §10.M про архитектуру
      мониторинга и §10.0.12–10.0.16 про уроки деплоя

### Production задачи

- [ ] Взять любой non-critical alert (HighCPU / LowDisk в off-hours),
      отреагировать самостоятельно, написать write-up
- [ ] Настроить новый alert для клиентского сервиса

### Read

- Prometheus: "First steps" + "Querying basics"
- [PromLabs promql-tutorial](https://promlabs.com/promql-cheat-sheet/) 30 мин
- [GOLD Signals](https://sre.google/sre-book/monitoring-distributed-systems/) — Google SRE Chapter 6
- `deploy/yandex/README.md` §10.M — наша архитектура мониторинга

### Check-in

1. Различие `rate()` vs `irate()` vs `increase()`?
2. Как устроен Alertmanager routing (P1/P2/P3)?
3. Зачем `for: 10m` в правиле alert'а?
4. 4 GOLD signals — назови и дай пример PromQL для каждого
5. Почему Alertmanager шлёт email через Stalwart :25, а не Postbox :465?
6. Как работает node-exporter textfile collector?
7. Почему `state-timeline`, а не `status-history` для gauge-метрик?

### DoD

- Развёрнут мониторинг-стек на test-VM
- Построен GOLD signals дашборд (по скриншоту show-and-tell)
- Отреагировал на 1+ реальный alert самостоятельно
- Добавил 2+ новых alert-правила


## Материал проекта: `docs/training/week_04.md`

<!-- SOURCE docs/training/week_04.md 7d3ed0a8799825ab -->

## Week 4 · Backup & Recovery (restic + DR)

### Цель

Уметь установить restic на новый tenant, настроить расписание, провести
smoke DR, объяснить клиенту RTO/RPO, интегрировать бэкап-метрики в
мониторинг.

---

### 1. Restic на VM: полная установка с нуля

#### 1.1. Установка бинарника

```bash
## На VM
curl -LO https://github.com/restic/restic/releases/download/v0.16.4/restic_0.16.4_linux_amd64.bz2
bzip2 -d restic_0.16.4_linux_amd64.bz2
sudo mv restic_0.16.4_linux_amd64 /usr/local/bin/restic
sudo chmod +x /usr/local/bin/restic
restic version  # → restic 0.16.4
```

#### 1.2. S3-репозиторий (Yandex Object Storage)

```bash
## Создаём bucket в YC Console: Object Storage → Create bucket
## Имя: <client-slug>-backups-prod, класс: STANDARD

## Секреты
sudo tee /etc/restic/env.sh > /dev/null << 'EOF'
export AWS_ACCESS_KEY_ID=<YC IAM access key>
export AWS_SECRET_ACCESS_KEY=<YC IAM secret>
export RESTIC_REPOSITORY=s3:https://storage.yandexcloud.net/<bucket-name>
export RESTIC_PASSWORD=<32+ символьный пароль шифрования>
EOF
sudo chmod 600 /etc/restic/env.sh
sudo chown root:root /etc/restic/env.sh
```

#### 1.3. Инициализация репозитория

```bash
source /etc/restic/env.sh
restic init
## → created restic repository
```

#### 1.4. Скрипт бэкапа

```bash
sudo mkdir -p /opt/restic-scripts /var/log/restic /var/lib/node_exporter/textfile_collector

sudo tee /opt/restic-scripts/backup.sh > /dev/null << 'SCRIPT'
#!/bin/bash
set -euo pipefail
LOG="/var/log/restic-backup.log"
METRICS_DIR="/var/lib/node_exporter/textfile_collector"
METRICS_FILE="${METRICS_DIR}/restic_backup.prom"
HOSTNAME="node-01"
REPO="<client-slug>-prod"
TIMESTAMP=$(date +%s)
STATUS=0
BYTES=0

source /etc/restic/env.sh

write_metrics() {
    local status=$1 timestamp=$2 bytes=$3
    mkdir -p "$METRICS_DIR"
    local tmp="${METRICS_FILE}.tmp"
    cat > "$tmp" << EOF
restic_backup_success{host="${HOSTNAME}",repo="${REPO}"} ${status}
restic_backup_timestamp_seconds{host="${HOSTNAME}",repo="${REPO}"} ${timestamp}
restic_backup_size_bytes{host="${HOSTNAME}",repo="${REPO}"} ${bytes}
EOF
    mv "$tmp" "$METRICS_FILE"
}

write_metrics 2 "$TIMESTAMP" 0

BACKUP_PATHS=("/etc" "/home" "/root" "/opt" "/var/www" "/var/lib/docker/volumes" "/var/lib/caddy")

EXISTING_PATHS=()
for p in "${BACKUP_PATHS[@]}"; do
    [[ -d "$p" ]] && EXISTING_PATHS+=("$p")
done

if restic backup "${EXISTING_PATHS[@]}" --tag auto --tag "$HOSTNAME" --compression auto --json 2>&1 | tee -a "$LOG"; then
    STATUS=1
    BYTES=$(grep -E '^\{"message_type":"summary"' "$LOG" | tail -1 | grep -oE '"total_bytes_processed":[0-9]+' | cut -d: -f2 || echo "0")
else
    STATUS=0; BYTES=0
fi

restic forget --tag "$HOSTNAME" --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --keep-yearly 1 --prune --compact 2>&1 | tee -a "$LOG" || true

if [[ $(date +%u) -eq 7 ]]; then
    restic check 2>&1 | tee -a "$LOG" || true
fi

write_metrics "$STATUS" "$TIMESTAMP" "$BYTES"
exit $(( 1 - STATUS ))
SCRIPT

sudo chmod +x /opt/restic-scripts/backup.sh
```

#### 1.5. Systemd timer (ежедневно 02:00)

```bash
sudo tee /etc/systemd/system/restic-backup.service > /dev/null << 'EOF'
[Unit]
Description=MSP Restic Backup
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/restic/env.sh
ExecStart=/opt/restic-scripts/backup.sh
Nice=19
IOSchedulingClass=best-effort
TimeoutStartSec=7200
SyslogIdentifier=restic-backup
EOF

sudo tee /etc/systemd/system/restic-backup.timer > /dev/null << 'EOF'
[Unit]
Description=MSP Restic Backup Timer

[Timer]
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now restic-backup.timer

## Проверяем
systemctl list-timers | grep restic
```

#### 1.6. Первый бэкап вручную

```bash
sudo systemctl start restic-backup
sudo journalctl -u restic-backup --since "5 min ago"

## Проверяем метрики
cat /var/lib/node_exporter/textfile_collector/restic_backup.prom
## restic_backup_success{...} 1  ← успех
```

---

### 2. Мониторинг бэкапов в Grafana

Метрики из §1.4 видны в Prometheus через node-exporter textfile collector.

**Dashboard "MSPShield — Backups"** (uid: `mspshield-backups`):

| Panel | Что показывает | PromQL |
|-------|---------------|--------|
| Статус | OK/FAIL/RUNNING | `restic_backup_success` |
| Размер | bytes | `restic_backup_size_bytes` |
| Возраст | секунды с последнего | `time() - restic_backup_timestamp_seconds` |
| 7 дней | история (state-timeline) | `restic_backup_success` range |
| Retention | текст | static `vector(1)` |

**Alert-правила** (`rules/backups.yml`):

| Alert | Severity | Триггер |
|-------|----------|---------|
| BackupFailed | P1 | `restic_backup_success == 0` |
| BackupMissed24h | P1 | `time() - timestamp > 93600` |
| BackupSizeDropped | P2 | `size < avg[7d] * 0.5` |
| BackupInProgress | P3 | `success == 2 for 30m` |

---

### 3. DR (Disaster Recovery) drill

#### 3.1. Список снапшотов

```bash
source /etc/restic/env.sh
restic snapshots --latest 5
```

#### 3.2. Восстановление одного файла

```bash
restic restore <snapshot-id> --target /tmp/restore-test --include /etc/caddy/Caddyfile
diff /etc/caddy/Caddyfile /tmp/restore-test/etc/caddy/Caddyfile
## → no differences = OK
rm -rf /tmp/restore-test
```

#### 3.3. Полное восстановление на новой VM

```bash
## На новой VM:
## 1. Установить restic
## 2. Скопировать /etc/restic/env.sh
## 3. Восстановить всё:
source /etc/restic/env.sh
restic restore latest --target /tmp/full-restore

## 4. Копировать нужные данные на место:
sudo cp -a /tmp/full-restore/var/lib/docker/volumes/* /var/lib/docker/volumes/
sudo cp -a /tmp/full-restore/var/lib/caddy/* /var/lib/caddy/
sudo cp -a /tmp/full-restore/etc/caddy/Caddyfile /etc/caddy/
## ... и т.д.
```

#### 3.4. Verify (целостность репозитория)

```bash
source /etc/restic/env.sh
restic check            # быстрая проверка метаданных
restic check --read-data  # полная (долго, читать все pack files)
```

---

### 4. Что бэкапим (чеклист)

| Путь | Что внутри | Критичность |
|------|-----------|-------------|
| `/etc` | Конфиги ОС, systemd, UFW | Высокая |
| `/home` | Пользовательские данные | Средняя |
| `/root` | Root home | Средняя |
| `/opt` | Приложения, скрипты | Высокая |
| `/var/www` | Лендинг/сайт | Средняя |
| `/var/lib/docker/volumes` | Все Docker volumes | **Критическая** |
| `/var/lib/caddy` | SSL-сертификаты | **Критическая** |

**Retention:** daily 7, weekly 4, monthly 6, yearly 1
**S3 bucket:** `<client-slug>-backups-prod`
**Verify:** каждую неделю (воскресенье)

---

### Задачи

- [ ] Развернуть restic на test-VM от нуля (§1)
- [ ] Сделать первый бэкап, проверить метрики в Prometheus
- [ ] Провести DR drill: восстановить один файл (§3.2)
- [ ] Настроить Grafana Backups dashboard
- [ ] Сессия с owner: 30 мин про restic internals (pack files,
      snapshots, prune)

### Production

- [ ] Пройти R-backup-failed: симулируй ошибку, исправь по runbook'у
- [ ] Подготовить monthly report для 1 Bronze-клиента

### Read

- [Restic docs: "Operations"](https://restic.readthedocs.io/en/latest/060_forget.html)
- `deploy/yandex/monitoring/restic-exporter/README.md` — наши скрипты
- `deploy/yandex/README.md` §15 — что бэкапится

### Check-in

1. Что такое `restic prune` и почему он дорогой?
2. RTO и RPO — формулируй для Bronze / Silver / Gold
3. Что делать если `restic check` показал `repository broken`?
4. Как restic-метрики попадают в Prometheus?
5. Что будет если забыть `/var/lib/caddy` в BACKUP_PATHS?

### DoD

- Самостоятельно провёл DR smoke-test
- Restic-метрики видны в Grafana
- Monthly report сдан


## Материал проекта: `docs/training/week_05.md`

<!-- SOURCE docs/training/week_05.md cf83e02f935a967b -->

## Week 5 · Networking + AmneziaWG

### Цель

Понимать архитектуру MSPShield overlay: bastion + tenant subnets.
Уметь заводить нового tenant, диагностировать VPN-проблемы.

### Задачи

- [ ] Прочитать `technical/0_Common/amneziawg/tenant_add.sh` построчно.
- [ ] Сессия с owner: 1 час про TCP/IP, `iptables` NAT, `ip route`,
      `mtu`.
- [ ] Завести test-tenant на тестовом bastion: сгенерить ключи,
      подключиться с ноутбука, пройти pinog 10.9.0.1.
- [ ] Прочитать R-08 (VPN tunnel down) и разобрать пошагово.
- [ ] ⚠️ **Урок из деплоя:** На test-VM проверить SSH-опции для
      preemptible: `-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL`.
      Обсудить с owner почему это важно (host keys меняются при рестарте,
      без static IP DNS устаревает). См. `deploy/yandex/README.md` §10.0.3.

### Production

- [ ] Под supervision завести нового tenant-peer'а для существующего
      клиента (если будет запрос).
- [ ] Отреагировать на один P3 по VPN (если случится в неделю),
      либо симулировать и пройти R-08.

### Read

- AmneziaWG whitepaper (первые 5 страниц — достаточно).
- `man awg` + `man awg-quick`.

### Check-in

1. Чем AmneziaWG отличается от OpenVPN и IPsec (в двух словах)?
2. Что такое `AllowedIPs` и зачем?
3. Как проверить, что peer включён и работает?

### DoD

- Развернул test-tenant на своих ресурсах.
- Понимает overlay 10.9/24 и tenant-subnets.
- Может без помощи запустить R-08.


## Материал проекта: `docs/training/week_06.md`

<!-- SOURCE docs/training/week_06.md 5f86306641fb7dad -->

## Week 6 · Security (hardening, SIEM basics)

### Цель

Применять security-хrategies осознанно. Уметь поднять minimal SIEM
(Wazuh или Loki+Alerts). Понимать 152-ФЗ в контексте нашей работы.

### Задачи

- [ ] Прочитать `deploy/nginx/mspshield.conf` (внимательно к CSP и
      security headers).
- [ ] Сессия с owner: 1 час про SSH hardening, fail2ban, ufw. 1 час
      про 152-ФЗ baseline.
- [ ] На test-VM: провести full hardening (SSH config, PAM, auditd,
      fail2ban), сравни до/после через `lynis audit system`.
- [ ] Прочитать R-01 (Ransomware) и обсудить с owner: что самое
      сложное в этом runbook'е.

### Production

- [ ] Провести security-audit одного Bronze-клиента: SSH-конфиги,
      fail2ban-логи, updates, firewall; зафиксировать findings в Kaiten.
- [ ] Закрыть 1-2 P3 security-related (force password rotation,
      revoke user access).

### Read

- [NIST SSH config guidelines](https://www.ssh.com/academy/ssh/sshd_config).
- Briefly: [Wazuh intro](https://wazuh.com/documentation/ossec/getting-started/) для Gold (опционально).

### Check-in

1. Что входит в твой SSH hardening checklist (5+ пунктов)?
2. Зачем `audit` логи кроме journalctl?
3. Как мы защищаем персональные данные в 152-ФЗ (основные принципы)?

### DoD

- Lynis-score test-VM поднят до 80+ после hardening.
- Security-audit одного Bronze подан.
- Может запустить R-01 по шагам.


## Материал проекта: `docs/training/week_07.md`

<!-- SOURCE docs/training/week_07.md e23025f184b853b5 -->

## Week 7 · Active Directory + GPO

### Цель

Разобраться с Microsoft AD на уровне достаточном для Silver/Gold
клиентов. Диагностировать типичные проблемы.

### Задачи

- [ ] Поднять тестовый Windows Server с AD DS на VM (demo license
      180 дней).
- [ ] Пройти full R-05 (AD replication failure) на демо-стенде.
- [ ] Прочитать с owner `docs/runbooks/R-05.md` и обсудить каждую команду.
- [ ] Создать GPO для disable USB storage, применить, проверить.

### Production

- [ ] Под supervision — password reset через AD у Silver-клиента.
- [ ] Проверить `ad_replication_lag` metric по всем Silver/Gold.

### Read

- [Microsoft Docs: Troubleshoot AD replication](https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/troubleshoot-active-directory-replication-problems).
- `dcdiag /?` и `repadmin /?`.

### Check-in

1. Что проверяет `dcdiag` (минимум 3 теста)?
2. FSMO роли — что это и как посмотреть?
3. Типичная причина AD replication lag?

### DoD

- Поднял тестовый AD-домен самостоятельно.
- Может пройти R-05 от первого шага до последнего.
- Под supervision выполнил production AD-операцию.


## Материал проекта: `docs/training/week_08.md`

<!-- SOURCE docs/training/week_08.md 9292482ad5b45022 -->

## Week 8 · 1С и специфика РФ

### Цель

Уметь диагностировать и фиксить типичные проблемы 1С:Предприятие.
Понимать import-substitution pipeline (Astra/RED).

### Задачи

- [ ] Прочитать R-04 (1С не запускается/тормозит).
- [ ] Сессия с owner: 1 час про архитектуру 1С (клиент-серверный vs
      файловый режим), 1 час про PostgreSQL для 1С и его тюнинг.
- [ ] На test-VM поднять 1C Demo (бесплатная версия) + PostgreSQL,
      провести fresh-install базы.

### Production

- [ ] Проверить `pg_stat_activity` одного клиента, найти long-running
      queries.
- [ ] Под supervision — закрыть 1 P2 по 1С.

### Read

- 1С-официальная документация по серверной установке.
- [Habr: 1С на PostgreSQL тюнинг](https://habr.com/ru/articles/) — свежие статьи.
- Briefly: [Astra Linux wiki](https://wiki.astralinux.ru/) — установка и
  особенности.

### Check-in

1. Чем отличается клиент-серверный и файловый режим 1С?
2. Типичные причины «1С не открывается после обновления»?
3. Что такое `maintenance_work_mem` в Postgres и как он влияет на 1С?

### DoD

- Поднят свой тестовый 1С-стенд.
- Закрыт 1 P2 по 1С под supervision.
- Знает, куда смотреть при долгих запросах в 1С.


## Материал проекта: `docs/training/week_09.md`

<!-- SOURCE docs/training/week_09.md 461263dc164f140f -->

## Week 9 · Ansible + IaC

### Цель

Писать свои Ansible playbooks / roles. Работать с Terraform в режиме
read-and-modify (не полный design-from-scratch).

### Задачи

- [ ] Прочитать все наши playbook'и (`technical/0_Common/ansible/`).
- [ ] Сессия с owner: Ansible roles, variables, facts, handlers — 2
      часа.
- [ ] Написать свою роль `ssh_hardening` и применить на test-VM.
- [ ] Прочитать `infra/terraform/main.tf` построчно, разобрать с
      owner каждый ресурс.

### Production

- [ ] Пройти `patch_nondisruptive.yml` на 2-3 Bronze-клиентах без
      supervision.
- [ ] Добавить в существующую роль новую task (например, установка
      node_exporter).

### Read

- [Ansible best practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html).
- Official Terraform tutorials (1-2 quickstarts).

### Check-in

1. Разница `when:` vs `failed_when:` vs `changed_when:`?
2. Что такое `handlers` и когда они срабатывают?
3. Почему Terraform требует backend (S3/local)?

### DoD

- Написал и применил свою Ansible-роль.
- Применил patch-playbook на 2+ клиентах.
- Понимает структуру Terraform main + variables.


## Материал проекта: `docs/training/week_10.md`

<!-- SOURCE docs/training/week_10.md 2bf3667d44e1214f -->

## Week 10 · Incident response в deep-dive

### Цель

Самостоятельно вести P2 инциденты от alert до closure + post-mortem.

### Задачи

- [ ] Перечитать R-01..R-11.
- [ ] Сессия с owner: как ставить приоритеты при 2+ одновременных
      инцидентах.
- [ ] Напиши с нуля свой runbook (R-12 — предложить тему: например,
      «Зависание PostgreSQL»). Выложи на review в MR.

### Production

- [ ] Взять следующий P2 один (с owner на pre-warned standby).
- [ ] Написать post-mortem по post_mortem_template.

### Read

- `docs/post_mortem_template.md` — перечитать до автоматизма.
- [Google SRE Book · "Managing Incidents"](https://sre.google/sre-book/managing-incidents/).

### Check-in

1. Как ты решаешь, какой из 2 P2 брать первым?
2. Что значит blameless post-mortem?
3. Как выглядит escalation process, если ты залип?

### DoD

- Взял 1+ P2 один (с backup).
- Написал 1 post-mortem (принят).
- Написал 1 новый runbook (принят).


## Материал проекта: `docs/training/week_11.md`

<!-- SOURCE docs/training/week_11.md d368305b78bdd0da -->

## Week 11 · Communication + customer success

### Цель

Профессионально общаться с клиентами в моменты кризиса и в обычных
вопросах. Вести weekly-sync.

### Задачи

- [ ] Прочитать `docs/sales/email_templates.md`, `docs/onboarding/welcome_package.md`.
- [ ] Пары-роуминги с owner: «разыграй» 3 сценария — (1) клиент в
      панике на P1, (2) клиент недоволен ответом, (3) клиент просит
      услугу за рамками тарифа.
- [ ] Написать 2 коммерческих ответа на почту (templates), owner
      ревьюит.

### Production

- [ ] Присутствовать на weekly-sync 2 клиентов (слушаешь).
- [ ] Ведёшь свой первый weekly-sync с одним из крепких Bronze (owner
      молчит).

### Read

- Chapter 5 "On Being A Good Customer" из *Customer Success Economy*
  (Nick Mehta) — 1 час.
- `docs/burnout_guard.md` — еще раз.

### Check-in

1. Как ты отвечаешь, если клиент агрессивен на P1?
2. Как сказать «нет» клиенту, когда он просит addon вне контракта?
3. Что должно быть в weekly-sync для крепкого клиента?

### DoD

- Провёл 1 weekly-sync самостоятельно.
- 2 коммерческих письма одобрены.
- Может ролево проиграть 3 кризис-сценария.


## Материал проекта: `docs/training/week_12.md`

<!-- SOURCE docs/training/week_12.md f9e007774d292776 -->

## Week 12 · Go-live + самостоятельная неделя

### Цель

Пройти проверку под нагрузкой. Получить положительное решение о
прохождении испытательного.

### Задачи

- [ ] **Четверг: self-drive day.** Весь день (9–18) junior ведёт
      тикеты самостоятельно. Owner не вмешивается, только read-only
      watch. Эскалация возможна **только** если реальный блок.
- [ ] Junior ведёт 2 weekly-sync (разные клиенты).
- [ ] Написать 1 runbook chapter с нуля (принять на review).
- [ ] Self-review: написать 1-2 страницы «что изменилось за 12 недель,
      что ещё хочется развивать, какие цели на next 3 мес».

### Feedback-сессия (конец недели)

60 минут 1-на-1 с owner:

- Owner делает 360-review: что вижу, что изменилось, где есть
  пробелы.
- Junior делает свой self-review (выше).
- Совместно формулируем 3 skill-цели на квартал.
- Обсуждаем график пересмотра зарплаты (типично: через 3 мес после
  прохождения испытательного).

### Acceptance criteria для прохождения

- ≥ 80% тикетов self-drive day закрыты без эскалации owner'у.
- Weekly-sync проведён без жалоб от клиента.
- Runbook сдан.
- Self-review читается как осознанный, а не формальный.

### Если не прошёл

- **Честный разговор.** Продлить испытательный на 1-2 мес ИЛИ
  расторгнуть с честным feedback'ом.
- Специфичный improvement-plan в Kaiten с SMART-задачами.


## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
