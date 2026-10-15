# Grafana — MSPShield Theme

## Календарь backup (15.10.2026)

Календарь встроен в существующий **MSPShield — Backups** (`/d/mspshield-backups`, панель 5), заменяя state-timeline: матрица «host × дата МСК» в палитре лендинга, без внешнего panel plugin. Отдельный календарный dashboard удалён. Exporter `scripts/backup_calendar.py` читает реальную историю `restic_backup_success` и `restic_backup_timestamp_seconds` из Prometheus; systemd `backup-calendar.timer` обновляет textfile каждые 5 минут. Зелёный — успешный наблюдавшийся job; серый — нет наблюдений. Это не подтверждение restore и не доказательство сохранности snapshot.

Файлы units находятся в `deploy/yandex/monitoring/`. На VM exporter установлен в `/opt/msp-tools/backup_calendar.py`; вывод — `/var/lib/node_exporter/textfile_collector/backup_calendar.prom`. При возрасте export >15 минут календарь скрывается. `verify_calendar.py` проверяет provisioned dashboard и серии, не печатая credentials. Для выбранного repo текущая матрица имеет семь дат; короткий сбой между scrape может не попасть в историю — подробный audit jobs требует отдельного журнала выполнения.

Новый dashboard появляется после доставки JSON на VM и provisioning scan; `git push` сам по себе файлы на сервер не доставляет. Точное совпадение со screenshot не проверено без визуального просмотра.

Каталог содержит всё необходимое, чтобы Grafana 10.4 на ВМ выглядела как часть сайта **msp-claude.online**: кремовый фон, лесной зелёный бренд, шрифты Cormorant Garamond + DM Sans + DM Mono.

---

## 📂 Структура

```
grafana/
├── grafana.ini                          # Конфиг сервера (light theme, ru-RU, home dashboard)
├── dashboards/                          # JSON-дашборды (auto-provisioned)
│   └── mspshield-overview.json          # Главный дашборд: CPU/RAM/Disk/Containers/SSL
├── provisioning/
│   ├── dashboards/dashboards.yml        # Provider — забирает *.json из dashboards/
│   └── datasources/prometheus.yml       # Datasource → http://prometheus:9090
├── theme/
│   └── mspshield.css                    # CSS-оверрайд (cream/forest палитра + шрифты)
└── README.md                            # ← этот файл
```

---

## 🎨 Палитра (соответствует CSS-токенам сайта)

| Назначение     | Цвет        | HEX       | HSL                |
|----------------|-------------|-----------|--------------------|
| Фон страницы   | cream       | `#f7f4ee` | `42 36% 95%`       |
| Карточки       | white       | `#ffffff` | —                  |
| Бренд / UP     | forest      | `#1b4d3e` | `162 49% 20%`      |
| Hover / акцент | forest-lt   | `#2d6b58` | `162 41% 30%`      |
| Warning        | amber       | `#b45309` | `25 90% 37%`       |
| Down / Error   | red         | `#b91c1c` | `0 72% 42%`        |
| Вторич. текст  | stone       | `#78746a` | `40 7% 45%`        |
| Основ. текст   | ink         | `#1a1815` | `36 10% 10%`       |

**Шрифты:** Cormorant Garamond (заголовки), DM Sans (тело), DM Mono (числа в Stat).

---

## 🚀 Деплой

```bash
# 1. Скопировать обновлённые файлы на ВМ
scp -r deploy/yandex/monitoring/grafana ubuntu@<IP>:/opt/msp/Newbie/deploy/yandex/monitoring/

# 2. Перезапустить только Grafana (без остановки Prometheus)
ssh ubuntu@<IP> "cd /opt/msp/Newbie/deploy/yandex/monitoring && docker compose up -d grafana"

# 3. Открыть SSH-туннель и зайти
ssh -L 3000:127.0.0.1:3000 ubuntu@<IP>
# → http://127.0.0.1:3000  (admin / $GRAFANA_ADMIN_PASSWORD)
```

После старта Grafana автоматически:

1. Создаст datasource **Prometheus** (`provisioning/datasources/prometheus.yml`)
2. Подгрузит дашборд **MSPShield Overview** в папку `MSPShield`
3. Откроет его как home dashboard (`default_home_dashboard_path` в `grafana.ini`)
4. Применит light theme (`GF_DEFAULT_THEME=light`)

---

## ✅ Проверка темы

```bash
ssh ubuntu@<IP> "docker logs msp-grafana 2>&1 | grep -i theme"
# Должно быть: theme=light
```

В UI:

- Открыть **Profile → Preferences** → **Theme** должна быть `Light`
- Открыть Overview → цвета thresholds: зелёный `#1b4d3e` для UP, красный `#b91c1c` для DOWN
- Header → `MSPShield` (если у вас Enterprise — иначе остаётся Grafana logo)

---

## 🧩 Подключение кастомного CSS (опционально)

CSS-оверрайд в `theme/mspshield.css` монтируется в `/usr/share/grafana/public/build/mspshield/`. Чтобы Grafana его подгружала, нужен один из двух подходов:

### Вариант 1 — патч `index.html` (быстро, ломается при апгрейде Grafana)

```bash
ssh ubuntu@<IP> "docker exec -u 0 msp-grafana sh -c \
'sed -i \"s|</head>|<link rel=stylesheet href=public/build/mspshield/mspshield.css></head>|\" \
 /usr/share/grafana/public/views/index.html'"
docker compose restart grafana
```

⚠️ Этот патч **сбрасывается** при `docker compose pull` или смене image версии — придётся применять заново.

### Вариант 2 — собственный Docker image (правильно)

```dockerfile
FROM grafana/grafana:10.4.2
COPY mspshield.css /usr/share/grafana/public/build/mspshield/mspshield.css
RUN sed -i 's|</head>|<link rel=stylesheet href=public/build/mspshield/mspshield.css></head>|' \
  /usr/share/grafana/public/views/index.html
```

```yaml
# В docker-compose.yml меняем:
grafana:
build: ./grafana/theme   # вместо image: grafana/grafana:10.4.2
```

---

## ➕ Добавить новый дашборд

1. Создать JSON в `dashboards/<name>.json`
2. Использовать палитру из таблицы выше для `thresholds.steps[].color`
3. Доставить проверенный JSON в смонтированный каталог VM; провижионер подхватит за 30 секунд (`updateIntervalSeconds: 30`).

Шаблон threshold-блока:

```json
"thresholds": {
"mode": "absolute",
"steps": [
  { "color": "#1b4d3e", "value": null },
  { "color": "#b45309", "value": 0.7 },
  { "color": "#b91c1c", "value": 0.9 }
]
}
```

---

## 🔧 Troubleshooting

| Симптом                                  | Причина                                          | Фикс                                            |
|------------------------------------------|--------------------------------------------------|-------------------------------------------------|
| Тема осталась dark                       | `.env` переопределяет `GF_DEFAULT_THEME=dark`    | Убрать переменную из `.env` или явно `=light`   |
| Дашборд не появился в UI                 | JSON невалиден / нет `uid`                       | `docker logs msp-grafana \| grep -i provision`  |
| Datasource не подключился                | Prometheus ещё не healthy                        | Подождать 30s или перезапустить grafana         |
| CSS не применился                        | `index.html` не пропатчен                        | См. секцию "Подключение кастомного CSS"         |
| 401 при логине                           | Пароль из `.env` не совпадает с тем что в БД     | Проверить учётную запись, согласовать reset через Grafana CLI; не удалять volume |
| Кастомные шрифты не подгружаются         | CSP/внешний источник                              | Использовать системные/local fonts; не отключать CSP ради оформления |

---

## 📐 Стандарты для новых панелей

- **Радиус карточек:** `4px` (как `--radius` сайта)
- **Тени:** едва заметные, `rgba(26, 24, 21, 0.04-0.10)`
- **Промежутки:** Grafana grid 24 колонки — выравнивать по 6 / 8 / 12
- **Названия панелей:** короткие, без эмодзи, в стиле "CPU Usage", "Container Memory"
- **Units:** обязательно — `percentunit` для долей, `bytes` для памяти, `d` для дней
- **Refresh:** `30s` для overview, `1m` для долгих окон, `10s` только если правда нужно

---

**Версия темы:** 1.0.0 (2026-06-03)
**Поддерживает:** Grafana 10.4.x (light theme только)
