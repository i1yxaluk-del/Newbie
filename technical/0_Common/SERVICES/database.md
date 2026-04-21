# Сервис: База данных (Postgres / MS SQL)

> **Сложность:** ⭐⭐⭐⭐☆. Junior — после L2 и модуля 1С (часто БД обслуживается в связке с 1С).
> **Тарифы:** мониторинг Bronze, тюнинг Silver, репликация/HA Gold.

## Типовые БД у клиентов

| СУБД | Доля | Используется под | Экспортёр |
|---|---|---|---|
| PostgresPro 14/15/16 | 40% | 1С, веб-сайты, свой софт | `postgres-exporter` |
| MS SQL 2019/2022 | 25% | 1С на Windows, WMS | `sql_exporter` |
| MySQL / MariaDB | 20% | WordPress, WooCommerce | `mysqld_exporter` |
| Postgres OSS (14/15/16) | 10% | Веб-сайты, Python/Node | `postgres-exporter` |
| MongoDB | 5% | Аналитика | `mongodb_exporter` |

## 1. ПРИЁМ

```markdown
1. СУБД + версия (SELECT version()): _______________________
2. Размер всех БД (GB): _______________________
3. Топ-3 по размеру: _______________________
4. Конфиг-файл (postgresql.conf / my.cnf): путь _______________________
5. shared_buffers / innodb_buffer_pool: ____ (должно быть ≈ 25% RAM хоста)
6. Реплика: есть / нет (master-slave / hot-standby)
7. Бэкап: pg_dump / pg_basebackup / .bak / mysqldump / прочее
8. PITR (WAL archiving) настроен: да / нет
9. Авто-vacuum (autovacuum/schedule): default / custom
10. Пользователи с правами: SUPERUSER/sa — сколько и кому?
11. TLS: включён / нет; SCRAM-SHA-256 (Postgres): да / нет
```

**Красные флаги:**
- MS SQL 2014/2016 — уже EOL (нет security updates)
- Postgres 10/11/12 — EOL, обновить минимум до 14
- `autovacuum = off` — катастрофа через год
- Бэкап только `pg_dump` без WAL → потеря до 24ч при сбое
- `pg_hba.conf` с `trust` в сети клиента

## 2. ПОДКЛЮЧЕНИЕ

### 2.1. Экспортёр метрик

**PostgresPro / Postgres OSS:**
```yaml
# docker-compose fragment
services:
  postgres-exporter:
    image: quay.io/prometheuscommunity/postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://mspshield_mon:${PG_MON_PWD}@db-srv:5432/postgres?sslmode=require"
    ports: ["9187:9187"]
    restart: unless-stopped
```

Пользователь `mspshield_mon` создаётся с минимальными правами:
```sql
CREATE USER mspshield_mon WITH PASSWORD '...';
GRANT pg_monitor TO mspshield_mon;
GRANT CONNECT ON DATABASE postgres TO mspshield_mon;
```

**MS SQL:**
```yaml
services:
  sql-exporter:
    image: burningalchemist/sql_exporter
    volumes:
      - ./sql_exporter.yml:/config/sql_exporter.yml:ro
      - ./queries:/etc/sql_exporter/queries:ro
```

Минимальные права:
```sql
CREATE LOGIN mspshield_mon WITH PASSWORD = '...';
USE master;
CREATE USER mspshield_mon FOR LOGIN mspshield_mon;
GRANT VIEW SERVER STATE TO mspshield_mon;
GRANT VIEW ANY DEFINITION TO mspshield_mon;
```

### 2.2. Бэкап

**Postgres (с PITR):**

```bash
# WAL archiving в postgresql.conf
# archive_mode = on
# archive_command = 'wal-g wal-push %p'

# Ежедневный base backup
wal-g backup-push /var/lib/postgresql/15/main
# WAL-G автоматически лечит/ротирует

# Ретеншн: 7 daily + 4 weekly
wal-g delete retain FULL 11 --confirm
```

WAL-G шифрует и заливает в S3 (Yandex). Один из самых надёжных open-source tools.

**MS SQL:**

```sql
-- Полный бэкап раз в неделю, дифф ежедневно, WAL (TRN) каждые 15 минут
BACKUP DATABASE [example] TO DISK = 'D:\sql-backups\example_full.bak' WITH COMPRESSION;
BACKUP LOG [example] TO DISK = 'D:\sql-backups\example_log.trn';
-- Затем restic tail → S3
```

## 3. АЛЕРТЫ

```yaml
- alert: DB_Down
  expr: pg_up == 0 or up{job="sql-exporter"} == 0
  for: 2m
  labels: { severity: critical, service: "db" }

- alert: DB_ReplicationLagHigh
  expr: pg_stat_replication_lag_bytes > 1e9    # > 1 GB
  for: 10m
  labels: { severity: warning, service: "db" }

- alert: DB_LongRunningQuery
  expr: pg_stat_activity_max_tx_duration{datname!~"postgres|template.*"} > 300
  for: 5m
  labels: { severity: warning, service: "db" }

- alert: DB_CacheHitRatioLow
  expr: (sum(rate(pg_stat_database_blks_hit[5m])) / (sum(rate(pg_stat_database_blks_hit[5m])) + sum(rate(pg_stat_database_blks_read[5m])))) < 0.95
  for: 30m
  labels: { severity: info, service: "db" }

- alert: DB_DeadlockSurge
  expr: rate(pg_stat_database_deadlocks[15m]) > 0.1
  labels: { severity: warning, service: "db" }

- alert: DB_BloatHigh
  expr: pg_bloat_ratio > 0.5
  labels: { severity: info, service: "db" }
  # → upsell: ADDON «VACUUM FULL + REINDEX в окне обслуживания»
```

## 4. КОНТРОЛЬ

### Еженедельно
- Размер БД тренд + прогноз заполнения диска
- Долгие запросы (pg_stat_statements топ-10)
- Статистика autovacuum — когда последний раз прошёл на больших таблицах
- WAL-архив без пробелов (wal-g backup-list)

### Ежемесячно
- Тестовое восстановление последней PITR-точки в sandbox
- Анализ медленных запросов с разработчиками клиента
- Обновление minor version (15.3 → 15.4)

### Ежеквартально
- VACUUM FULL на сильно разбухших таблицах (в окне обслуживания)
- Ротация паролей мониторинг-юзера
- Проверка репликации end-to-end

## 5. TROUBLESHOOTING

### 5.1. «БД тормозит»
```
1. pg_stat_activity — смотрим что сейчас выполняется
2. pg_stat_statements — топ медленных запросов (если установлен)
3. Проверить планы:
   EXPLAIN (ANALYZE, BUFFERS) <запрос>
4. Размер индексов (могут быть bloated) — pg_indexes_size()
5. Проверить конфиг shared_buffers, work_mem (часто на дефолте)

Для MS SQL:
   SELECT * FROM sys.dm_exec_requests
   DBCC SHOW_STATISTICS
   sys.dm_os_wait_stats
```

### 5.2. Диск заполнен
```
1. du -sh /var/lib/postgresql/15/main/*   # что занимает
2. Чаще всего — pg_wal (логи) разросся (archive не успевает / отключён)
3. Ещё вариант — одна большая таблица раздулась:
   SELECT schemaname, relname, pg_size_pretty(pg_total_relation_size(relid))
   FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;

4. Временно — добавить диск (Yandex Cloud online-resize), затем VACUUM FULL в окне.
```

### 5.3. Репликация отстала
```
1. pg_stat_replication — смотрим lag_bytes / lag_seconds
2. На реплике: select pg_last_wal_replay_lsn(), pg_last_xact_replay_timestamp()
3. Частые причины:
   - Медленный диск реплики (IOPS кончились)
   - Длинный запрос на реплике (hot_standby_feedback)
   - Сеть «моргнула» → recovery
4. Если lag > 5 минут и растёт — предложить rebuild реплики через pg_basebackup.
```

## Upsell

| Триггер | Предложение | Цена |
|---|---|---|
| БД > 100 ГБ, autovacuum не справляется | Тюнинг + партицирование | ADDON 35k₽ |
| Только pg_dump, без PITR | Внедрение WAL-G | ADDON 20k₽ |
| Нет реплики, HA нужен | Master + hot-standby | 40k₽ + VM |
| MS SQL 2016 EOL | Миграция 2019/2022 | Проект |
| Переход с MS SQL на PostgresPro | Миграция + тестирование | Проект 80–150k₽ |

## Чек-лист junior

- [ ] Поставил postgres-exporter и увидел метрики
- [ ] Создал read-only мониторинг-юзера с минимальными правами
- [ ] Запустил WAL-G backup и восстановил БД в тестовом окружении
- [ ] Умею читать pg_stat_statements и находить топ-10 медленных
- [ ] Знаю разницу VACUUM vs VACUUM FULL (и когда нельзя использовать последнее)
- [ ] Понимаю: MS SQL — отдельная вселенная, частые ADDON «тюнинг» передаём senior
