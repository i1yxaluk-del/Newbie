# Сервис: 1С:Предприятие (сервер)

> **Сложность:** ⭐⭐⭐⭐☆ (продвинутая). Junior допускается после L1-экзамена.
> **Тарифы:** Bronze (мониторинг) → Silver (+ автоматизация и логи) → Gold (+ security).
> **Критичность бизнеса:** **КРИТИЧЕСКАЯ** — при остановке 1С встаёт весь офис, бухгалтерия,
> склад, продажи.

## Почему 1С — отдельная история

1С — закрытая система с нестандартными метриками. Нельзя просто поставить
«один агент». Требуется 3 слоя мониторинга:

1. **Хост ОС** — node_exporter (Linux) или windows_exporter (Windows)
2. **Приложение** — rphost/ragent процессы, количество сеансов, CPU/RAM по ним
3. **База данных** — PostgresPro или MS SQL, свой экспортёр

---

## Типовые инсталляции у клиентов

| Вариант | Частота | ОС | БД | Наш подход |
|---|---|---|---|---|
| Файловая (2–5 юзеров) | 30% | Windows 10/11 | — (файл) | Мониторинг шары + бэкап .1CD |
| Клиент-сервер малый | 40% | Windows Server | MS SQL Express / PostgresPro | Полный мониторинг + бэкап |
| Клиент-сервер средний | 25% | Windows/Linux Server | PostgresPro | Полный + репликация БД |
| Отказоустойчивый кластер | 5% | Linux (Astra/RHEL) | PostgresPro Ent | Расширенный + HA-мониторинг |

---

## 1. ПРИЁМ сервиса

```markdown
### Опросник: 1С клиента

1. Версия платформы: 8.3.__   (минимально 8.3.20, оптимально 8.3.25+)
2. Режим: [Файловый / Клиент-серверный]
3. Конфигурация(и): [ERP 2.5 / УТ 11 / УНФ / Бухгалтерия 3.0 / своя]
4. Где развёрнут сервер: [Windows Server ____ / Linux _____]
5. СУБД: [MS SQL 20__ / PostgresPro __.__]
6. Размер базы (ГБ): __
7. Количество одновременных сеансов (пик): __
8. Регламентные задания: есть / нет
9. Кто обслуживает 1С: [1С-франчайзи / внутренний специалист / никто]
10. Бэкапы: куда, как часто, проверялись ли восстановлением: __
11. Критичные сервисы на сервере: [обмены с сайтом / обмены с банком / ФНС / Честный знак / ...]
12. Есть ли тестовая база (для проверки бэкапов): да / нет
13. Лицензии 1С: [USB-ключ / программная / облачная]
```

**Красные флаги:**
- Платформа 8.3.17 и старше — уязвимости, неподдерживаемо
- Бэкап только силами `Конфигуратор → Выгрузка` раз в неделю
- Нет тестовой базы — мы не сможем проверить restore
- Одна нода без реплики при нагрузке > 20 пользователей
- USB-ключ в продовом сервере без резерва (клиент потеряет лицензию при сбое)

---

## 2. ПОДКЛЮЧЕНИЕ

### 2.1. Хост (Windows / Linux)

**Windows Server:**
```powershell
# PowerShell от админа
Invoke-WebRequest -Uri https://mspshield.ru/install/windows_exporter.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
# Скрипт открывает 9182, service windows_exporter, автозапуск
```

**Linux (Astra / RHEL / Ubuntu):**
```bash
sudo bash /opt/mspshield/CLIENT/node_exporter/install_linux.sh
# → exposes :9100
```

### 2.2. Метрики 1С приложения

На сервере 1С доступен технологический журнал (ТЖ) + RAS/RAC-интерфейс:

```xml
<!-- C:\Program Files\1cv8\conf\logcfg.xml -->
<config xmlns="http://v8.1c.ru/v8/tech-log">
  <log location="C:\1c-logs" history="24">
    <event>
      <eq property="Name" value="EXCP"/>     <!-- исключения -->
    </event>
    <event>
      <eq property="Name" value="TDEADLOCK"/>  <!-- deadlocks БД -->
    </event>
    <event>
      <eq property="Name" value="DBMSSQL"/>    <!-- SQL-запросы -->
      <ge property="Duration" value="10000"/>  <!-- > 10 сек -->
    </event>
  </log>
</config>
```

Далее запускаем наш парсер **1c-exporter** (Python + promtail):

```bash
# Свой scraper на основе https://github.com/qorel/1c-exporter (fork)
docker run -d --name 1c-exporter \
  -v C:\1c-logs:/logs:ro \
  -p 9999:9999 \
  --restart unless-stopped \
  mspshield/1c-exporter:latest \
  --log-path=/logs
```

Метрики, которые получаем:
- `onec_sessions_total{infobase="..."}` — активные сеансы по БД
- `onec_rphost_memory_bytes` — память rphost.exe
- `onec_exceptions_total` — исключения за минуту
- `onec_slow_queries_total{duration_gt="10s"}` — медленные SQL
- `onec_deadlocks_total` — deadlocks
- `onec_license_status` — USB-ключ жив или нет

### 2.3. Мониторинг СУБД

**PostgresPro:**
```bash
# На сервере БД (Linux/Windows)
docker run -d --name postgres-exporter \
  -e DATA_SOURCE_NAME="postgresql://monitor:pass@localhost:5432/?sslmode=disable" \
  -p 9187:9187 \
  quay.io/prometheuscommunity/postgres-exporter
```

**MS SQL Server:**
```bash
# sql_exporter с готовым конфигом для 1С-метрик
# https://github.com/burningalchemist/sql_exporter
docker run -d --name sql-exporter \
  -v /opt/sql-exporter.yml:/config/sql_exporter.yml \
  -p 9399:9399 \
  burningalchemist/sql_exporter
```

### 2.4. Бэкапы 1С — самое важное

Правило: **2 независимых метода бэкапа**, минимум.

**Метод А — средствами 1С (dt-выгрузка, конфигуратор):**
```batch
:: Windows · /opt/mspshield/client_configs/<slug>/1c_backup.bat
"C:\Program Files\1cv8\8.3.25.1257\bin\1cv8.exe" DESIGNER ^
  /S"srv1c:1541\ib_main" ^
  /N"admin" /P"%1C_PWD%" ^
  /DumpIB "D:\1c-backups\ib_main_%DATE%.dt" ^
  /UC"ONLY_FROM_BACKUP"
:: Затем restic в облако:
"C:\restic\restic.exe" -r s3:s3.yandexcloud.net/client-<slug>-backups backup D:\1c-backups\
```

**Метод Б — средствами СУБД:**
```bash
# PostgresPro: pg_basebackup + WAL-G для point-in-time restore
# MS SQL: .bak файлы через SQL Agent → restic
```

**ВАЖНО:** ежемесячно восстанавливаем бэкап в тестовую базу и делаем
функциональную проверку (клиент открывает — «всё на месте?»). См.
`../../../docs/checklists/monthly.md` → «Monthly restore drill».

---

## 3. НАСТРОЙКА алертов

```yaml
# добавить в bronze_alerts.yml или silver_alerts.yml (зависит от тарифа)

- alert: OneC_ServerDown
  expr: up{job="windows_exporter", hostname=~"srv-1c.*"} == 0
  for: 2m
  labels: { severity: critical, service: "1c" }
  annotations:
    summary: "Сервер 1С {{ $labels.hostname }} недоступен"
    runbook: "https://wiki.mspshield/runbooks/1c-server-down"

- alert: OneC_LicenseLost
  expr: onec_license_status == 0
  for: 1m
  labels: { severity: critical, service: "1c" }
  annotations:
    summary: "Потеряна лицензия 1С — все сеансы упадут!"

- alert: OneC_TooManyExceptions
  expr: rate(onec_exceptions_total[5m]) > 0.5
  for: 10m
  labels: { severity: warning, service: "1c" }
  annotations:
    summary: "Более 0.5 исключений/сек в 1С {{ $labels.infobase }}"

- alert: OneC_SlowQueriesSurge
  expr: rate(onec_slow_queries_total[10m]) > 2
  for: 15m
  labels: { severity: warning, service: "1c" }

- alert: OneC_Deadlock
  expr: increase(onec_deadlocks_total[15m]) > 0
  for: 0s
  labels: { severity: warning, service: "1c" }

- alert: OneC_DB_SizeHigh
  expr: pg_database_size_bytes / (1024*1024*1024) > 50
  for: 1h
  labels: { severity: info, service: "1c" }
  annotations:
    summary: "База 1С превысила 50 ГБ — время задуматься о выгрузках/сжатии"
    # upsell triger: предложить ADDON «оптимизация 1С-базы»

- alert: OneC_BackupStale
  expr: time() - onec_backup_last_success_ts > 86400 * 2
  for: 10m
  labels: { severity: critical, service: "1c" }
  annotations:
    summary: "Бэкап 1С не выполнялся > 2 дней"
```

---

## 4. КОНТРОЛЬ

### Еженедельно
- Размер базы (тренд роста)
- Средн. время отклика формы списка документов (если есть нагрузочный тест)
- Количество ошибок ТЖ
- Длительные фоновые задания
- Статус последнего бэкапа + тестовое восстановление

### Ежемесячно
- Restore drill: развернуть последний бэкап в тестовую базу и открыть клиентом
- Обновление платформы 1С (если вышла стабильная релиз-версия)
- Чистка журнала регистрации (`ЖурналРегистрации` — разрастание убивает БД)

### Ежеквартально
- ТОиР: VACUUM / REINDEX в PostgresPro, DBCC CHECKDB в MS SQL
- Обновление конфигурации (согласование с 1С-франчайзи)
- Тест переключения на резервный ключ (если SoftKey / программная лицензия)

---

## 5. TROUBLESHOOTING

### 5.1. Сервер 1С не запускается
```
1. Проверить службу:
   Windows: Get-Service 1C:Enterprise* ; Start-Service '1C:Enterprise 8.3 Server Agent'
   Linux:   systemctl status srv1cv8-8.3.25 ; journalctl -u srv1cv8-*.service -n 100

2. Проверить ragent.log в C:\Program Files\1cv8\srvinfo\reg_1541\
   или /opt/1cv8/x86_64/8.3.25/srv1cv8 (Linux)

3. Частые причины:
   - Не запустилась СУБД (PostgresPro служба упала)
   - USB-ключ отсоединился (physical / VM passthrough)
   - Закончилось место на диске под temp
   - Повреждение srvinfo (требует восстановления из бэкапа)

4. Эскалация → 1С-франчайзи клиента (с кратким описанием шагов 1-3)
```

### 5.2. «1С тормозит» (универсальная жалоба)
```
1. Собрать факты:
   - Когда начало тормозить?
   - У всех или у отдельных пользователей?
   - В каких операциях (списки, проведение документа, отчёт)?
   - После каких изменений?

2. Посмотреть метрики:
   - CPU/RAM rphost.exe (grafana dashboard «1С-health»)
   - Размер БД vs свободное место диска
   - Rate slow_queries_total
   - pg_stat_activity / sp_who2

3. Стандартные действия:
   a) Перезапуск rphost на менее загруженный процесс (ragent)
   b) Очистка сеансов «зависшие пользователи» (RAS cluster cleanup)
   c) Если regularly — оптимизация конкретных запросов (эскалация к 1С-франчайзи)
   d) VACUUM ANALYZE (PostgresPro) — если давно не делали

4. Upsell:
   - Если БД > 50 ГБ и растёт — ADDON «реструктуризация + перенос архива»
   - Если рост сеансов выше лимита железа — ADDON «подбор нового сервера»
```

### 5.3. Deadlock / блокировки
```
1. В логе ТЖ искать event TDEADLOCK
2. В Grafana смотреть onec_deadlocks_total
3. Если повторяется на одних и тех же объектах:
   → документировать, передать 1С-франчайзи как «оптимизация блокировок»
```

### 5.4. Потеря лицензии
```
1. Срочно! Все сеансы падают.
2. Проверить USB-ключ:
   - Windows: Панель управления → HASP License Manager → статус
   - Linux: /etc/init.d/haspd status
3. Перезапустить службу лицензий:
   net start "HASP License Manager"
   или systemctl restart haspd
4. Если USB-ключ физически повреждён — клиент вызывает 1С-франчайзи
   на замену (мы не можем сами — у нас нет прав на партнёрский кабинет 1С).
```

---

## Upsell / cross-sell

| Триггер | Предложение | Цена-ориентир |
|---|---|---|
| БД > 50 ГБ, тормозит | Реструктуризация + архив | ADDON 45–80k ₽ |
| Версия 8.3.17 и младше | Апгрейд платформы | ADDON 15–25k ₽ |
| Нет резерва USB-ключа | Переход на программную лицензию | ADDON 8k ₽ |
| Нет тестовой базы | Развёртывание тестового контура | ADDON 12k ₽ + VM |
| Сеансов > 30 регулярно | HA-кластер 1С (active-passive) | Проект, ~200k ₽ |
| Обмены с сайтом/банком нестабильны | Монитор обменов + алерты | Входит в Silver |
| 152-ФЗ ПДн в базе | Шифрование и аудит доступа | Требует Gold |

См. [`../../ADDONS.md`](../../ADDONS.md) — полный прайс.

---

## Чек-лист junior: «готов принимать `1C`»

- [ ] Понимаю разницу файлового и клиент-серверного режима
- [ ] Знаю где лежат логи платформы (logcfg, ТЖ, ЖР)
- [ ] Развернул 1c-exporter на учебном стенде
- [ ] Умею снять dt-бэкап и восстановить в тестовую базу
- [ ] Знаю отличия PostgresPro monitoring от MS SQL
- [ ] Прогнал TROUBLESHOOTING сценарии 5.1 и 5.2
- [ ] Понимаю границу ответственности MSPShield vs 1С-франчайзи
