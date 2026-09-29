# Инцидент: важность, инструкция, подтверждение и разбор

Инцидент — нарушение или угроза услуге. Severity задаёт бизнес-влияние и порядок реакции. Runbook применяется только после проверки триггера. Сначала ограничивают ущерб и восстанавливают услугу, затем ищут корневую причину, если поиск не мешает восстановлению.

Хронология содержит время наблюдения, решение, действие и результат. Клиент получает факты, влияние, следующий срок обновления и временную меру — без догадок. Postmortem не ищет виновного; он создаёт проверяемое изменение: тест, алерт, ограничение или обновлённую инструкцию.

Runbook не отменяет мышление: неожиданное состояние — стоп и эскалация, а не импровизация в production.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

## Материал проекта: `docs/runbooks/README.md`

<!-- SOURCE docs/runbooks/README.md 26eb1c917363f5b7 -->

## Runbooks MSPShield

> Стандартизированные инструкции для реакции на типовые инциденты и
> плановые работы. Исполняются 1-в-1 без импровизации — любая импровизация
> фиксируется как incident note в post-mortem.

---

### Структура runbook-файла

```
## R-XX · <Название>

### Severity: P1 / P2 / P3 / P4
### Tier: Bronze / Silver / Gold / all
### Time budget: <мин>
### Requires: <доступы / инструменты>

### 1. Триггер
### 2. Диагностика (как убедиться, что runbook применим)
### 3. Действия (по шагам)
### 4. Откат (как вернуть, если всё стало хуже)
### 5. Проверка (как убедиться, что фикс сработал)
### 6. Коммуникация (что сообщить клиенту)
### 7. Post-actions (что документировать, когда кого-то дообучить)
```

---

### Каталог

#### Общие процедуры

| Имя | Название | Severity | Tier | Ссылка |
|---|---|:-:|:-:|---|
| R-01 | Ransomware alert / подозрительная активность | P1 | all | [R-01.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-01.md) |
| R-02 | Полная потеря доступа к серверу | P1 | all | [R-02.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-02.md) |
| R-03 | Backup failed / corrupt | P1 | all | [R-03.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-03.md) |
| R-04 | 1С не запускается / тормозит | P2 | all | [R-04.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-04.md) |
| R-05 | AD replication failure | P2 | Silver/Gold | [R-05.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-05.md) |
| R-06 | Disk space critical (>90%) | P2 | all | [R-06.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-06.md) |
| R-07 | SSL expired / expiring | P2 / P3 | all | [R-07.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-07.md) |
| R-08 | VPN/AmneziaWG tunnel down | P2 | all | [R-08.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-08.md) |
| R-09 | User access lost (reset password) | P3 | all | [R-09.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-09.md) |
| R-10 | Monthly patch window | P4 (планово) | all | [R-10.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-10.md) |
| R-11 | DR drill (ежеквартально) | P4 (планово) | all | [R-11.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-11.md) |

#### Мониторинг (автоматические алерты)

| Имя | Название | Severity | Ссылка |
|---|---|:-:|---|
| R-site-down | Сайт недоступен | P1 | [R-site-down.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-site-down.md) |
| R-backend-down | Backend недоступен | P1 | [R-backend-down.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-backend-down.md) |
| R-vault-down | Vaultwarden недоступен | P1 | [R-vault-down.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-vault-down.md) |
| R-imap-down | IMAP недоступен | P1 | [R-imap-down.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-imap-down.md) |
| R-smtp-down | SMTP недоступен | P1 | [R-smtp-down.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-smtp-down.md) |
| R-node-down | Node Exporter недоступен | P1 | [R-node-down.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-node-down.md) |
| R-container-down | Контейнер не работает | P1 | [R-container-down.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-container-down.md) |
| R-backup-failed | Бэкап завершился с ошибкой | P1 | [R-backup-failed.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-backup-failed.md) |
| R-backup-missed | Бэкап не запускался >26 ч | P1 | [R-backup-missed.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-backup-missed.md) |
| R-ssl-expired | SSL-сертификат истёк | P1 | [R-ssl-expired.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-ssl-expired.md) |
| R-grafana-down | Grafana недоступен | P2 | [R-grafana-down.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-grafana-down.md) |
| R-restart-loop | Рестарт-луп контейнера | P2 | [R-restart-loop.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-restart-loop.md) |
| R-container-mem | Контейнер — RAM >90% лимита | P2 | [R-container-mem.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-container-mem.md) |
| R-high-cpu | CPU >90% | P2 | [R-high-cpu.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-high-cpu.md) |
| R-high-mem | RAM >95% | P2 | [R-high-mem.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-high-mem.md) |
| R-low-disk | Мало места на диске (<10%) | P2 | [R-low-disk.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-low-disk.md) |
| R-backup-size-dropped | Размер бэкапа упал >50% | P2 | [R-backup-size-dropped.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-backup-size-dropped.md) |
| R-ssl-expire | SSL истекает (<14 дней) | P2 | [R-ssl-expire.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-ssl-expire.md) |
| R-slow | Сервис — медленный ответ | P3 | [R-slow.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-slow.md) |
| R-site-slow | Сайт — медленный ответ | P3 | [R-site-slow.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-site-slow.md) |
| R-5xx | Высокий процент ошибок 5xx | P3 | [R-5xx.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-5xx.md) |
| R-backup-long | Бэкап выполняется >30 мин | P3 | [R-backup-long.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-backup-long.md) |

---

### Правила обновления

- Runbook меняется **только** через Pull Request в Kaiten с обзором.
- Каждое применение runbook → комментарий в карточке: сработал / не сработал / нюанс.
- Раз в 3 месяца — review всех runbook: что добавить, что изменить.

---

*Обновлено: v5.0 · 2026-06*


## Материал проекта: `docs/runbooks/R-01.md`

<!-- SOURCE docs/runbooks/R-01.md 4eecbc8600f31e0d -->

## R-01 · Ransomware alert / подозрительная активность

**Severity:** P1
**Tier:** all
**Time budget:** 60 мин до стабилизации, затем полный DR
**Requires:** Wazuh (Gold) или Loki-alerts, root на серверах, доступ к бэкапам, канал связи с клиентом (Telegram и/или MAX)

---

### 1. Триггер

- Alert из Wazuh/Kaspersky: «shadow copy deleted», «mass file rename»,
  «encryption activity detected».
- Alert из Loki: скачок logins failed + sudo activity из нетипичного IP.
- Пользователи жалуются: «все файлы стали .locked / .crypt / unreadable».
- Записка с требованием выкупа обнаружена в shared folder.

---

### 2. Диагностика (первые 5 минут)

Выполнить параллельно:

```bash
## На затронутом сервере
ls -la /var/lib/<service>/ | head -20   # шифрованные ли файлы?
ps auxf | grep -vE '(COMMAND|\[)'       # подозрительные процессы?
journalctl -u sshd -n 100 | grep -E 'Accepted|Failed'
last -n 20                               # кто залогинен был?
find / -newer /tmp/marker -mmin -30 -type f 2>/dev/null | head -30
```

**Критерии подтверждения ransomware:**
- Масса файлов с одинаковым новым расширением.
- Файл README.txt / HOW_TO_DECRYPT.txt в затронутых папках.
- Shadow copies удалены (`vssadmin list shadows` — Windows) или snapshots (Linux LVM/ZFS).

---

### 3. Действия

#### 3.1. Немедленная изоляция (первые 10 мин)

- [ ] **Изолировать** затронутые серверы от сети: `iptables -I INPUT -j DROP; iptables -I OUTPUT -j DROP` (НЕ выключать — для forensics).
- [ ] **НЕ перезагружать** (в RAM могут быть ключи расшифровки — бывает).
- [ ] Снять снапшот VM (если cloud) — для forensics.
- [ ] Залогиниться на **соседние серверы**, применить превентивную изоляцию (отключить shares).

#### 3.2. Оповещение (параллельно)

- [ ] Telegram/MAX клиента (в выбранном при онбординге мессенджере): «Зафиксирован incident P1. Подробности в течение 30 мин».
- [ ] Звонок ЛПР клиента — голосом объяснить ситуацию.
- [ ] Внутренний Kaiten: создать карточку инцидента с severity=P1.

#### 3.3. Forensics (первые 30 мин, параллельно с восстановлением)

- [ ] Собрать:
  - `ps auxf > /tmp/ps_<timestamp>.txt`
  - `netstat -tulnp > /tmp/net_<timestamp>.txt`
  - `/var/log/auth.log`, `/var/log/secure`
  - `/var/log/wazuh/alerts.log` (Gold)
  - Запись в Kaiten: timeline (точки времени, что сделано).
- [ ] Определить **точку входа** (какая учётка, откуда IP, какой exploit).
- [ ] Определить **scope** (какие серверы затронуты, какие shares, есть ли доступ к AD).

#### 3.4. Восстановление

**Вариант A · Восстановление из бэкапа (предпочтительный):**

- [ ] Идентифицировать последний чистый бэкап (до ransomware).
- [ ] Создать **новый** сервер (fresh install) — не восстанавливаем поверх заражённого.
- [ ] Восстановить данные через restic:
  ```bash
  restic -r <repo> restore <snapshot_id> --target /mnt/restore
  ```
- [ ] Пройти по restored data антивирусом (Kaspersky) ДО включения в сеть.
- [ ] После проверки — включить в сеть, переподключить пользователей.

**Вариант B · Если бэкапов нет / все заражены:**

- [ ] Определить, есть ли известный декриптор (nomoreransom.org).
- [ ] Если нет — **переговоры с выкупателями НЕ ведём** (юридические риски, и обычно не расшифровывают).
- [ ] Клиенту откровенно говорим: «Данные недоступны, восстановление невозможно. Строим инфру с нуля».

#### 3.5. Смена компрометированных кредентиалов

- [ ] Все пароли админов (на всех серверах клиента, не только затронутых).
- [ ] Все SSH-ключи.
- [ ] Все API-токены 3-party сервисов.
- [ ] AD: смена паролей всех привилегированных пользователей.
- [ ] VPN: ротация pre-shared ключей / WireGuard keys.
- [ ] Fail2ban ban IP с которого шёл атака (если вычислен).

---

### 4. Откат

Откат **не применим** (мы НЕ восстанавливаем в заражённую среду). Если
восстановление привело к новым проблемам (например, несовместимость
версий) — **создаём новую fresh install** ещё раз, не возвращаемся в compromised state.

---

### 5. Проверка

- [ ] Затронутые сервисы доступны.
- [ ] Нет новых encryption events в Wazuh за последние 2 часа.
- [ ] Антивирусный сканер проходит чисто.
- [ ] Пользователи могут работать с данными.
- [ ] Test-restore бэкапа подтверждён (чтобы знать, что backup-chain теперь чистая).

---

### 6. Коммуникация с клиентом

#### Первое сообщение (в течение 30 мин):

> Зафиксирован инцидент P1 — подозрение на ransomware.
> Мы изолировали затронутые серверы, начали forensics и восстановление.
> Ожидаемое время возврата к работе — `<N>` часов.
> Следующий апдейт — через 2 часа.

#### Последующие апдейты — каждые 2 часа до стабилизации.

#### Финальный post-mortem (в течение 48 часов после закрытия):

Полный отчёт по template в `docs/post_mortem_template.md`.

---

### 7. Post-actions

- [ ] Post-mortem опубликован (клиенту + внутренне).
- [ ] Технический долг: что позволило ransomware проникнуть — устранено.
  - Чаще всего: устаревшее ПО, слабые пароли RDP, отсутствие MFA, уязвимый VPN.
- [ ] Обновить runbook R-01: что сработало, что нет.
- [ ] Добавить тест в DR-drill (раз в квартал).
- [ ] Проверить, затронуты ли **другие клиенты** (если использовался общий компонент).
- [ ] Юридически: оценить необходимость уведомления РКН (если затронуты ПДн).

---

*Обновлено: v4.1 · 2026-04*


## Материал проекта: `docs/runbooks/R-02.md`

<!-- SOURCE docs/runbooks/R-02.md 87d2394807a561e6 -->

## R-02 · Полная потеря доступа к серверу

**Severity:** P1
**Tier:** all
**Time budget:** 30 мин до восстановления доступа или эскалации
**Requires:** доступ к cloud-панели, console/VNC, резервные SSH ключи

---

### 1. Триггер

- SSH не отвечает (timeout / connection refused).
- Ping до сервера проходит, но порт 22 закрыт.
- Ping не проходит.
- Ранее работавший сервер ушёл из мониторинга Prometheus (scrape fail).

---

### 2. Диагностика

```bash
## С bastion
ping <host>                         # есть ли L3?
nc -zv <host> 22                    # порт открыт?
traceroute <host>                   # где теряется?
ssh -v <host>                       # verbose-лог ошибки
```

Проверить в cloud-панели:
- Статус VM (running / stopped / error).
- Recent operations (кто что делал за последний час).
- Security group / firewall rules.
- Cloud-init logs (если был reboot).

---

### 3. Действия

#### 3.1. Если SSH закрыт, но VM жива

- [ ] Открыть **serial console** в cloud-панели (Yandex Cloud / Selectel).
- [ ] Залогиниться root (пароль из Vaultwarden).
- [ ] Проверить статус sshd: `systemctl status sshd`.
- [ ] Проверить firewall: `iptables -L -n` / `ufw status`.
- [ ] Проверить `/var/log/auth.log` на последние запреты.

**Типичные причины:**
- fail2ban банул наш IP (нестандартный случай): `fail2ban-client unban <our_ip>`.
- Правило iptables добавлено ошибочно: найти и удалить.
- sshd упал из-за OOM или конфига: `systemctl restart sshd`.
- Пользователь сменил пароль / ключи — восстановить из бэкапа configs.

#### 3.2. Если VM не запускается

- [ ] Проверить последние операции в cloud (может, кто-то ресетил).
- [ ] Попробовать start.
- [ ] Если не стартует — посмотреть console logs / crash reason.
- [ ] Если железо VM повреждено:
  - Сделать снапшот диска.
  - Присоединить диск к новой VM.
  - Смонтировать, скопировать данные.
  - Запустить новую VM из snapshot / backup.

#### 3.3. Если сетевая связность пропала

- [ ] Проверить network ACL / route table в cloud.
- [ ] Проверить VPC peering (если используется).
- [ ] Проверить, не изменился ли IP.
- [ ] Проверить DNS (если клиент ходил по имени).

---

### 4. Откат

- Если мы сами что-то меняли — вернуть предыдущее состояние из git / Ansible.
- Если cloud-операцию отменить нельзя — восстановление из backup.

---

### 5. Проверка

- [ ] SSH отвечает.
- [ ] Критические сервисы `systemctl is-active`.
- [ ] Мониторинг видит сервер (node_exporter отдаёт метрики).
- [ ] Последний lookup в DNS правильный.

---

### 6. Коммуникация с клиентом

- Telegram и/или MAX сразу после триггера (в тот канал, который выбран клиентом): «Сервер <name> недоступен. Разбираемся».
- Апдейт каждые 15 мин до восстановления.
- Финальное: «Сервер работает. Причина: <..>. Post-mortem в течение 48ч».

---

### 7. Post-actions

- [ ] Post-mortem если простой >30 мин.
- [ ] Почему не было алерта раньше (если не было)?
- [ ] Что нужно мониторить дополнительно, чтобы такое не повторилось?
- [ ] Если проблема в cloud — eskalate в support провайдера.

---

*Обновлено: v4.1 · 2026-04*


## Материал проекта: `docs/runbooks/R-03.md`

<!-- SOURCE docs/runbooks/R-03.md 51fb8ecf5692f7c0 -->

## R-03 · Backup failed / corrupt

**Severity:** P1 (если последний чистый бэкап старше RPO)
**Tier:** all
**Time budget:** 2 часа до восстановленного backup-chain
**Requires:** root на целевом сервере, access to S3, restic repo password

---

### 1. Триггер

- Alert «backup job failed» из cron / systemd timer → Prometheus.
- `restic check` возвращает ошибки.
- Объём бэкапов не растёт (= не пишут новые данные).
- Тест-restore fails.

---

### 2. Диагностика

```bash
## На сервере с бэкап-агентом
systemctl status restic-backup.timer
journalctl -u restic-backup.service -n 200
restic -r <repo> check --read-data-subset=5%
restic -r <repo> snapshots
```

**Что проверяем:**
- Когда был последний успешный snapshot.
- Ошибка: сеть / auth / disk full / corrupted chunk.
- Место в S3 бакете (квота).
- Доступ к S3: `aws --endpoint-url=... s3 ls s3://<bucket>/`.

---

### 3. Действия

#### 3.1. Если ошибка сетевая / auth

- [ ] Проверить credentials в `/etc/restic/env`.
- [ ] Rotate IAM ключи (в Яндекс.Cloud — создать новые service account keys).
- [ ] Перезапустить: `systemctl start restic-backup.service`.

#### 3.2. Если corrupted chunk

- [ ] `restic -r <repo> rebuild-index`.
- [ ] `restic -r <repo> prune --max-repack-size 10G`.
- [ ] Повторить `restic check`.
- [ ] Если не помогает — создать **новый** репозиторий и переинициализировать backup (старый не удалять 30 дней).

#### 3.3. Если quota full в S3

- [ ] `restic forget --keep-last 10 --prune` (если retention политика позволяет).
- [ ] Увеличить бакет-квоту (это 5 мин в панели).
- [ ] Проверить, нет ли «левых» объектов в бакете (кто-то залил не через restic).

#### 3.4. Если test-restore fails

- [ ] Попробовать restore на **другой** snapshot (может быть, только этот corrupted).
- [ ] Если все свежие сломаны — eskalate до последнего чистого из S3 archive.
- [ ] Объявить клиенту, что RPO нарушен (и на какое время).

---

### 4. Откат

Откат невозможен (нельзя «вернуть» сломанный snapshot). Единственный
путь — починить chain и создать новый чистый bckup.

---

### 5. Проверка

- [ ] Последние 3 snapshot успешны.
- [ ] `restic check` passes.
- [ ] Test-restore (любой 1 файл) в tmp работает.
- [ ] Следующий scheduled backup job прошёл нормально.

---

### 6. Коммуникация с клиентом

- Если RPO нарушен >4h — Telegram/MAX клиенту с объяснением.
- Если мы восстановили chain в течение 1 часа без потери данных — регулярный
  weekly-отчёт упомянет event, отдельное оповещение не нужно.

---

### 7. Post-actions

- [ ] Почему не было замечено раньше (raid quality check работает?)
- [ ] Возможные причины (quota, credentials expired, network flakiness) — добавить в мониторинг.
- [ ] Если это было у 1 клиента — проверить у **всех других** такую же проблему (проактивно).
- [ ] Update runbook R-03 если нюанс новый.

---

*Обновлено: v4.1 · 2026-04*


## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
