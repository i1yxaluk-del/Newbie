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

| № | Название | Severity | Tier | Ссылка |
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

---

## Правила обновления

- Runbook меняется **только** через Pull Request в Kaiten с обзором.
- Каждое применение runbook → комментарий в карточке: сработал / не сработал / нюанс.
- Раз в 3 месяца — review всех runbook: что добавить, что изменить.

---

*Обновлено: v4.1 · 2026-04*
