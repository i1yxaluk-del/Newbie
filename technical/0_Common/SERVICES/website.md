# Сервис: Корпоративный сайт / лендинг

> **Сложность:** ⭐☆☆☆☆ (начальная). Идеальный первый сервис для junior.
> **Тариф:** входит в **Bronze** и выше.
> **Критичность бизнеса:** средняя (простой = упущенные заявки, но не остановка компании).

## Что типично у клиентов B2B

| Вариант | Доля | Где обычно хостится | Кто владелец |
|---|---|---|---|
| WordPress / Bitrix | 60% | Timeweb, Beget, SpaceWeb, reg.ru | Маркетолог клиента |
| Headless (React + Node) | 20% | Yandex Cloud, Selectel | IT-отдел |
| Статика на CDN | 10% | Yandex CDN, Cloudflare R2 | Разработчик-подрядчик |
| Self-hosted (свой сервер) | 10% | VPS клиента | Часто — сам клиент, без SLA |

**Наша зона ответственности** зависит от варианта:
- Shared hosting (1–2) → только **внешний мониторинг доступности + SSL-срок**. Всё остальное у хостера.
- Свой сервер → **полный мониторинг** (CPU, диск, nginx/apache) + бэкапы сайта.

---

## 1. ПРИЁМ сервиса (Discovery)

Junior заполняет опросник с клиентом за 10 минут:

```markdown
### Опросник: Сайт клиента

1. Основной домен: _______________________
2. Дополнительные домены/поддомены: _______________________
3. Где хостится (провайдер): _______________________
4. CMS/движок: [WordPress / Bitrix / Тильда / Свой / ... ]
5. SSL-сертификат: Let's Encrypt (auto) / платный (куплен до __.__.____) / нет
6. Кто развивает сайт (агентство/внутренний): _______________________
7. Есть ли доступ у клиента к серверу? [Да — root / Да — FTP / Нет — всё у подрядчика]
8. Где бэкап сайта: _______________________
9. Критичные формы на сайте (заявки → куда приходят): _______________________
10. Когда последний раз падал: _______________________
```

**Красные флаги**, на которые junior обязан обратить внимание директора клиента:
- SSL просрочен или истекает < 30 дней
- CMS не обновлялся > 12 месяцев (WordPress 5.x, Bitrix 22.x и старше)
- Нет бэкапов, или «бэкапы у предыдущего подрядчика»
- Сайт работает по HTTP без редиректа на HTTPS
- Cookie / формы не соответствуют 152-ФЗ (нет баннера согласия)

---

## 2. ПОДКЛЮЧЕНИЕ к мониторингу

### 2.1. Самый простой случай — **внешний мониторинг (Bronze-base)**

Для shared hosting и любого сайта, к которому нет доступа к серверу:

```yaml
# technical/1_Bronze/EXECUTOR/prometheus/prometheus.yml
# Добавить новый job:

- job_name: blackbox_http_2xx
  metrics_path: /probe
  params:
    module: [http_2xx]
  static_configs:
    - targets:
        - https://example.ru                # основной сайт клиента
        - https://example.ru/audit          # важная страница (как в MSPShield — /audit)
        - https://shop.example.ru           # поддомены
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: blackbox-exporter:9115
    - target_label: client
      replacement: example-llc             # имя клиента в grafana
```

**Что мы контролируем:**
- HTTP-код ответа (должен быть 200/301/302)
- Время ответа (алерт если > 3 сек)
- SSL-сертификат (алерт за 14 дней до истечения)
- Редиректы (сайт должен резолвиться и на www, и без www)

### 2.2. Если у нас есть SSH на сервер клиента

```bash
# Ставим node_exporter
sudo bash /opt/mspshield/CLIENT/node_exporter/install_linux.sh

# Дополнительно для nginx:
sudo apt install -y prometheus-nginx-exporter
# /etc/nginx/conf.d/stub_status.conf:
# server { listen 127.0.0.1:8080; location /stub_status { stub_status; allow 127.0.0.1; deny all; } }
sudo systemctl enable --now prometheus-nginx-exporter

# Для apache — apache_exporter:
# https://github.com/Lusitaniae/apache_exporter
```

### 2.3. Бэкап контента сайта

```bash
# /opt/mspshield/client_configs/<slug>/website_backup.sh
#!/usr/bin/env bash
# Ежедневный бэкап файлов сайта + БД WordPress/Bitrix

SITE_ROOT=/var/www/example.ru
DB_NAME=example_wp
DB_USER=wp_backup
B2_REPO="s3:s3.yandexcloud.net/client-example-backups"

# Дамп БД
mysqldump --single-transaction --quick "$DB_NAME" \
  | gzip > /tmp/${DB_NAME}_$(date +%F).sql.gz

# Архив файлов + БД → restic
restic -r "$B2_REPO" backup \
  "$SITE_ROOT" \
  /tmp/${DB_NAME}_*.sql.gz \
  --tag website --tag example-llc

# Очистка старых (retention: 7 daily + 4 weekly + 6 monthly)
restic -r "$B2_REPO" forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune

rm /tmp/${DB_NAME}_*.sql.gz
```

Разворачивается через systemd timer (шаблон есть в `1_Bronze/CLIENT/restic_backup/`).

---

## 3. НАСТРОЙКА — что включаем в alert rules

```yaml
# prometheus rules · bronze_alerts.yml · добавить:

- alert: WebsiteDown
  expr: probe_success{job="blackbox_http_2xx"} == 0
  for: 2m
  labels: { severity: critical, service: website }
  annotations:
    summary: "Сайт {{ $labels.instance }} недоступен"
    runbook: "https://wiki.mspshield/runbooks/website-down"

- alert: WebsiteSlowResponse
  expr: probe_duration_seconds{job="blackbox_http_2xx"} > 3
  for: 5m
  labels: { severity: warning, service: website }
  annotations:
    summary: "Сайт {{ $labels.instance }} отвечает медленно ({{ $value }}s)"

- alert: SslExpiringSoon
  expr: probe_ssl_earliest_cert_expiry - time() < 86400 * 14
  for: 15m
  labels: { severity: warning, service: website }
  annotations:
    summary: "SSL-сертификат {{ $labels.instance }} истекает через <14 дней"

- alert: WebsiteHigh5xx
  # Только если есть nginx_exporter
  expr: rate(nginx_http_requests_total{status=~"5.."}[5m]) > 1
  for: 10m
  labels: { severity: warning, service: website }
  annotations:
    summary: "На сайте {{ $labels.instance }} 5xx > 1 req/s"
```

### Grafana dashboard

Готовый JSON: `technical/0_Common/grafana/dashboards/website.json` (создаётся на старте клиента).
Панели:
- Uptime за последние 30 дней (% green)
- Response time p50/p95/p99
- SSL expiration countdown
- HTTP status codes distribution
- (если есть exporter) RPS + 5xx rate

---

## 4. КОНТРОЛЬ — еженедельно

В шаблоне `weekly_report.sh` выводим по сайту:

```
Сайт example.ru
  Uptime:       99.97% (downtime 13 мин всего — 1 инцидент)
  Response p95: 1.2 с (норма < 2 с) ✓
  SSL до:       15 июня 2026 (72 дня)
  Инциденты:    1 (24 апр, 08:12-08:25 — сбой на стороне хостера)
```

Если SSL < 30 дней — **красная метка в отчёте** и тикет на обновление.

---

## 5. TROUBLESHOOTING — стандартный протокол

### 5.1. Алерт `WebsiteDown`

```
1. Подтвердить извне (curl -I с другого IP):
   curl -sI https://example.ru | head -n 3

2. Проверить DNS:
   dig example.ru +short
   dig www.example.ru +short

3. Проверить ping сервера (если известен IP):
   ping -c 3 <ip>

4. Если shared hosting — открыть статус-страницу хостера
   (Timeweb: status.timeweb.ru, Beget: status.beget.com)

5. Если свой сервер:
   ssh srv-web-01
   systemctl status nginx
   tail -n 50 /var/log/nginx/error.log
   df -h    # место
   free -m  # память

6. Эскалация:
   - 15 минут без прогресса → уведомить клиента в чат
   - 30 минут → тикет у хостера / разработчика сайта
   - 1 час → пост-мортем после решения
```

### 5.2. Алерт `WebsiteSlowResponse`

```
1. curl -w "@curl-format.txt" -o /dev/null -s https://example.ru
   (разбивка: DNS, connect, TLS, TTFB, total)

2. Проверить нагрузку (если есть SSH):
   uptime
   top -b -n 1 | head
   ss -s    # кол-во соединений

3. Проверить nginx логи на долгие запросы:
   awk '$NF > 3' /var/log/nginx/access.log | tail -20

4. Проверить БД (если WP/Bitrix):
   mysql -e "SHOW PROCESSLIST" | grep -v Sleep

5. Частые причины:
   - DDoS / парсер-бот → включить rate-limit в nginx
   - Накручен кэш WordPress → очистить cache plugin
   - Выросла БД WooCommerce → предложить апгрейд SSD (ADDON)
   - Кончилось место на диске → расширить (ADDON)
```

### 5.3. Алерт `SslExpiringSoon`

```
1. Let's Encrypt — обычно auto-renew должен работать:
   certbot renew --dry-run

2. Если dry-run падает:
   - Проверить что 80 порт открыт для HTTP-01 challenge
   - Проверить /etc/letsencrypt/renewal/*.conf на корректность

3. Платный сертификат — нужно клиенту напомнить:
   - За 14 дней → предупреждение
   - За 7 дней → WARN с эскалацией директору
   - За 3 дня → CRITICAL + предложение Let's Encrypt как замену
```

---

## Upsell / cross-sell на сайте

Когда предлагать клиенту доп.услуги:

| Триггер у клиента | Предложение | Тариф/addon |
|---|---|---|
| Сайт на WordPress не обновлялся > 12 мес | Аудит безопасности + обновление | ADDON: 15–25k ₽ |
| Формы с ПДн без согласия | Имплементация 152-ФЗ баннера | ADDON: 8k ₽ |
| Рост нагрузки, slow response | Миграция на VPS с CDN | Оценка отдельно + Silver+ |
| Много поддоменов, WP multisite | Выделенный dashboard | Входит в Silver |
| Критичные заявки → падение = деньги | Gold с SLA 1ч | Апгрейд Gold |

См. также [`../../ADDONS.md`](../../ADDONS.md).

---

## Чек-лист junior: «я готов принимать сервис `website`»

- [ ] Знаю, как проверить uptime извне (curl / probe)
- [ ] Знаю разницу между shared hosting и own VPS (что мы можем и что нет)
- [ ] Умею добавить сайт в `prometheus.yml` под blackbox_exporter
- [ ] Знаю, как читать SSL-метрики и когда бить тревогу
- [ ] Прогнал protocol `WebsiteDown` на учебном стенде
- [ ] Понимаю, когда предложить upsell
