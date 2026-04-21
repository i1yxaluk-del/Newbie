# KSC — Kaspersky Security Center: Настройка для MSP
# Версия 2.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# Этот документ описывает:
#   - Развёртывание KSC в Docker (Linux)
#   - Начальную конфигурацию для MSP
#   - Управление несколькими клиентами (виртуальные серверы)
#   - Экспорт метрик для Prometheus
#
# Альтернатива: KSC Cloud Console (SaaS) — без локального деплоя
# ═══════════════════════════════════════════════════════════════════

## 1. ВАРИАНТЫ РАЗВЁРТЫВАНИЯ KSC

### Вариант A: KSC Cloud Console (рекомендуется для старта)

```
Преимущества:
  ✅ Нет необходимости в отдельной VM
  ✅ Автоматические обновления
  ✅ Kaspersky поддерживает HA
  ✅ Бесплатно до 300 устройств (MSP-лицензия)

Ссылка: https://ksc.kaspersky.ru/

Настройка:
  1. Зарегистрировать аккаунт на ksc.kaspersky.ru
  2. Создать "Виртуальный сервер" для каждого клиента MSP
  3. Скачать пакет установки агента из консоли
  4. Развернуть через GPO или вручную
```

### Вариант B: Локальный KSC на Windows Server

```
Требования:
  - Windows Server 2016/2019/2022
  - 4 vCPU, 8 GB RAM, 100 GB SSD
  - SQL Server Express (включён в дистрибутив)
  - Порты: 8080 (Web Console), 13000 (агенты), 13292

Загрузка:
  https://www.kaspersky.ru/small-to-medium-business-security/security-center
```

---

## 2. НАСТРОЙКА ВИРТУАЛЬНЫХ СЕРВЕРОВ (MULTI-TENANT)

```
Структура KSC для MSP:
  KSC Master Server (наш)
  ├── Виртуальный сервер "Клиент 1 — Bronze"
  │   └── Устройства клиента 1
  ├── Виртуальный сервер "Клиент 2 — Silver"
  │   └── Устройства клиента 2
  └── Виртуальный сервер "Клиент 3 — Gold"
      └── Устройства клиента 3

Преимущества виртуальных серверов:
  - Изоляция данных между клиентами
  - Отдельные политики для каждого
  - Возможность предоставить клиенту доступ только к его данным
```

### Создание виртуального сервера (KSC Console)

```
Консоль KSC → Иерархия серверов управления →
  → Создать виртуальный сервер администрирования →
    Имя: "CLIENT_NAME (Gold)"
    Адрес: 10.9.0.X
    Группы администраторов: создать MSP-Admin
```

---

## 3. ПОЛИТИКИ БЕЗОПАСНОСТИ (ШАБЛОН)

```
Базовая политика для Gold-клиента:
  Kaspersky Endpoint Security → Новая политика

  Компоненты защиты:
  ✅ Защита от файловых угроз — Рекомендуемый уровень
  ✅ Веб-Антивирус — Блокировать опасные сайты
  ✅ Защита от сетевых угроз — Включить
  ✅ Контроль программ — Режим "Запрещено по умолчанию" (для серверов)
  ✅ Управление уязвимостями и патчами — Сканировать каждые 24 ч
  ✅ Шифрование диска — для ноутбуков (BitLocker)

  Задачи:
  - Обновление БАЗ: каждые 4 часа
  - Полная проверка: еженедельно (воскресенье 02:00)
  - Быстрая проверка: ежедневно (07:00, перед началом работы)
  - Инвентаризация ПО: еженедельно
```

---

## 4. ЭКСПОРТ МЕТРИК ДЛЯ PROMETHEUS

### Скрипт опроса KSC REST API

```python
#!/usr/bin/env python3
"""
ksc_metrics_exporter.py — Экспорт метрик KSC для Prometheus
Файл: /opt/monitoring/scripts/ksc_exporter.py

Запуск: python3 ksc_exporter.py --ksc-url https://KSC_IP:8080 --port 9200
"""
import requests
import time
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl

KSC_URL      = os.getenv("KSC_URL", "https://localhost:8080")
KSC_USER     = os.getenv("KSC_USER", "KLAdmin")
KSC_PASSWORD = os.getenv("KSC_PASSWORD", "")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9200"))

session = requests.Session()
session.verify = False  # В production: указать путь к CA cert KSC

def ksc_login():
    """Аутентификация в KSC REST API."""
    resp = session.post(
        f"{KSC_URL}/api/v1.0/login",
        json={"wstrUser": KSC_USER, "wstrPassword": KSC_PASSWORD},
        timeout=10
    )
    resp.raise_for_status()

def get_hosts_count():
    """Получить количество управляемых устройств."""
    resp = session.post(
        f"{KSC_URL}/api/v1.0/HostGroup.FindHosts",
        json={
            "wstrFilter": "",
            "vecFieldsToReturn": ["KLHST_WKS_HOSTNAME"],
            "pOptions": {}
        },
        timeout=15
    )
    if resp.status_code == 200:
        return len(resp.json().get("pHostInfo", []))
    return -1

def get_threats_count():
    """Получить количество необработанных угроз."""
    resp = session.post(
        f"{KSC_URL}/api/v1.0/EventProcessing.GetEvents",
        json={
            "wstrFilter": "(EventType = 'GNRL_EV_VIRUS_FOUND') AND (EventStatus = 'KLEV_STATUS_PROCESSING')",
            "vecFieldsToReturn": ["EventId"],
            "pEventTypeOrder": {},
            "dwPage": 0,
            "dwNumPage": 100
        },
        timeout=15
    )
    if resp.status_code == 200:
        return resp.json().get("dwTotalItems", 0)
    return -1

def get_outdated_av_count():
    """Количество устройств с устаревшими базами (> 24 часов)."""
    # Упрощённая логика — в production использовать фильтр KSC
    return 0

def generate_metrics():
    """Генерировать текст метрик в формате Prometheus."""
    try:
        ksc_login()
        hosts = get_hosts_count()
        threats = get_threats_count()

        return f"""# HELP ksc_managed_hosts_total Total managed hosts in KSC
# TYPE ksc_managed_hosts_total gauge
ksc_managed_hosts_total {hosts}
# HELP ksc_unresolved_threats_total Unresolved security threats
# TYPE ksc_unresolved_threats_total gauge
ksc_unresolved_threats_total {threats}
# HELP ksc_scrape_success 1 if KSC API is reachable
# TYPE ksc_scrape_success gauge
ksc_scrape_success 1
"""
    except Exception as e:
        return f"""# HELP ksc_scrape_success 1 if KSC API is reachable
# TYPE ksc_scrape_success gauge
ksc_scrape_success 0
# HELP ksc_scrape_error_info Error info
# Error: {str(e)[:200]}
"""

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = generate_metrics().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass  # Тихий режим

if __name__ == "__main__":
    print(f"KSC Metrics Exporter starting on :{METRICS_PORT}")
    httpd = HTTPServer(("0.0.0.0", METRICS_PORT), MetricsHandler)
    httpd.serve_forever()
```

### Systemd unit для exporter

```ini
# /etc/systemd/system/ksc-exporter.service
[Unit]
Description=Kaspersky Security Center Metrics Exporter
After=network.target

[Service]
Type=simple
Environment=KSC_URL=https://10.9.0.4:8080
Environment=KSC_USER=KLAdmin
EnvironmentFile=/etc/ksc/ksc.env
ExecStart=/usr/bin/python3 /opt/monitoring/scripts/ksc_exporter.py
Restart=on-failure
RestartSec=30s

[Install]
WantedBy=multi-user.target
```

---

## 5. ИНТЕГРАЦИЯ С PROMETHEUS

```yaml
# Добавить в prometheus.yml:
- job_name: 'ksc-exporter'
  scrape_interval: 300s      # KSC API — раз в 5 минут достаточно
  static_configs:
    - targets: ['localhost:9200']
      labels:
        role: 'ksc'
        owner: 'executor'
```

---

## 6. ЧЕКЛИСТ ПЕРВОНАЧАЛЬНОЙ НАСТРОЙКИ KSC

```
После установки KSC:

Безопасность:
  [ ] Сменить пароль KLAdmin на сложный
  [ ] Настроить 2FA (если Cloud Console)
  [ ] Ограничить доступ к Web Console только из VPN (10.9.0.0/24)
  [ ] Настроить TLS-сертификат

Лицензирование:
  [ ] Добавить лицензию Kaspersky Endpoint Security
  [ ] Настроить автоматическое продление

Клиенты:
  [ ] Создать виртуальный сервер для каждого клиента
  [ ] Настроить базовую политику безопасности
  [ ] Настроить задачи обновления (каждые 4 часа)
  [ ] Настроить задачи сканирования

Уведомления:
  [ ] Настроить email/Telegram уведомления об угрозах
  [ ] Настроить ежедневный отчёт о состоянии защиты

Мониторинг:
  [ ] Развернуть ksc_metrics_exporter.py
  [ ] Добавить в Prometheus
  [ ] Проверить алерты в gold_alerts.yml
```
