# Runbooks MSPShield

> Стандартизированные инструкции для реакции на типовые инциденты и
> плановые работы. Исполняются 1-в-1 без импровизации — любая импровизация
> фиксируется как incident note в post-mortem.

---

## Структура runbook-файла

```
# R-XX · <Название>

## Severity: P1 / P2 / P3 / P4
## Tier: Bronze / Silver / Gold / all
## Time budget: <мин>
## Requires: <доступы / инструменты>

## 1. Триггер
## 2. Диагностика (как убедиться, что runbook применим)
## 3. Действия (по шагам)
## 4. Откат (как вернуть, если всё стало хуже)
## 5. Проверка (как убедиться, что фикс сработал)
## 6. Коммуникация (что сообщить клиенту)
## 7. Post-actions (что документировать, когда кого-то дообучить)
```

---

## Каталог

### Общие процедуры

| Имя | Название | Severity | Tier | Ссылка |
|---|---|:-:|:-:|---|
| R-01 | Ransomware alert / подозрительная активность | P1 | all | [R-01.md](R-01.md) |
| R-02 | Полная потеря доступа к серверу | P1 | all | [R-02.md](R-02.md) |
| R-03 | Backup failed / corrupt | P1 | all | [R-03.md](R-03.md) |
| R-04 | 1С не запускается / тормозит | P2 | all | [R-04.md](R-04.md) |
| R-05 | AD replication failure | P2 | Silver/Gold | [R-05.md](R-05.md) |
| R-06 | Disk space critical (>90%) | P2 | all | [R-06.md](R-06.md) |
| R-07 | SSL expired / expiring | P2 / P3 | all | [R-07.md](R-07.md) |
| R-08 | VPN/AmneziaWG tunnel down | P2 | all | [R-08.md](R-08.md) |
| R-09 | User access lost (reset password) | P3 | all | [R-09.md](R-09.md) |
| R-10 | Monthly patch window | P4 (планово) | all | [R-10.md](R-10.md) |
| R-11 | DR drill (ежеквартально) | P4 (планово) | all | [R-11.md](R-11.md) |

### Мониторинг (автоматические алерты)

| Имя | Название | Severity | Ссылка |
|---|---|:-:|---|
| R-site-down | Сайт недоступен | P1 | [R-site-down.md](R-site-down.md) |
| R-backend-down | Backend недоступен | P1 | [R-backend-down.md](R-backend-down.md) |
| R-vault-down | Vaultwarden недоступен | P1 | [R-vault-down.md](R-vault-down.md) |
| R-imap-down | IMAP недоступен | P1 | [R-imap-down.md](R-imap-down.md) |
| R-smtp-down | SMTP недоступен | P1 | [R-smtp-down.md](R-smtp-down.md) |
| R-node-down | Node Exporter недоступен | P1 | [R-node-down.md](R-node-down.md) |
| R-container-down | Контейнер не работает | P1 | [R-container-down.md](R-container-down.md) |
| R-backup-failed | Бэкап завершился с ошибкой | P1 | [R-backup-failed.md](R-backup-failed.md) |
| R-backup-missed | Бэкап не запускался >26 ч | P1 | [R-backup-missed.md](R-backup-missed.md) |
| R-ssl-expired | SSL-сертификат истёк | P1 | [R-ssl-expired.md](R-ssl-expired.md) |
| R-grafana-down | Grafana недоступен | P2 | [R-grafana-down.md](R-grafana-down.md) |
| R-restart-loop | Рестарт-луп контейнера | P2 | [R-restart-loop.md](R-restart-loop.md) |
| R-container-mem | Контейнер — RAM >90% лимита | P2 | [R-container-mem.md](R-container-mem.md) |
| R-high-cpu | CPU >90% | P2 | [R-high-cpu.md](R-high-cpu.md) |
| R-high-mem | RAM >95% | P2 | [R-high-mem.md](R-high-mem.md) |
| R-low-disk | Мало места на диске (<10%) | P2 | [R-low-disk.md](R-low-disk.md) |
| R-backup-size-dropped | Размер бэкапа упал >50% | P2 | [R-backup-size-dropped.md](R-backup-size-dropped.md) |
| R-ssl-expire | SSL истекает (<14 дней) | P2 | [R-ssl-expire.md](R-ssl-expire.md) |
| R-slow | Сервис — медленный ответ | P3 | [R-slow.md](R-slow.md) |
| R-site-slow | Сайт — медленный ответ | P3 | [R-site-slow.md](R-site-slow.md) |
| R-5xx | Высокий процент ошибок 5xx | P3 | [R-5xx.md](R-5xx.md) |
| R-backup-long | Бэкап выполняется >30 мин | P3 | [R-backup-long.md](R-backup-long.md) |

---

## Правила обновления

- Runbook меняется **только** через Pull Request в Kaiten с обзором.
- Каждое применение runbook → комментарий в карточке: сработал / не сработал / нюанс.
- Раз в 3 месяца — review всех runbook: что добавить, что изменить.

---

*Обновлено: v5.0 · 2026-06*
