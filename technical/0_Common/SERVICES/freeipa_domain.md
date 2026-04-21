# Сервис: FreeIPA (Linux-домен)

> **Сложность:** ⭐⭐⭐☆☆. Junior — после L2 и прохождения AD-модуля (концепции схожи).
> **Тарифы:** мониторинг на Silver, полное управление — Silver/Gold.
> **Критичность:** **КРИТИЧЕСКАЯ** — падение IPA = нет SSH/Kerberos/sudo у всех.

## Почему FreeIPA сейчас актуален в РФ 2026

- Импортозамещение Active Directory в гос/полугос сегменте
- Поставляется в составе **Astra Linux SE**, **РЕД ОС**, **ALT Server**, **RHEL / Rocky**
- Интегрирует: 389-DS (LDAP) + MIT Kerberos + Dogtag CA + BIND DNS + NTP + Sudo/HBAC
- Единый источник правды для Linux-парка

У наших клиентов встречается чаще в:
- Медицинских ИС на Astra Linux
- Научно-исследовательских центрах
- Компаниях, переезжающих с AD (hybrid-период через AD-trust)

---

## Типовые инсталляции

| Вариант | Клиентов | Конфигурация |
|---|---|---|
| Single server (обучающий) | 40% | 1 IPA server, < 30 хостов |
| Master + Replica | 50% | 2 сервера, < 150 хостов |
| Multi-site replica | 10% | 3+ IPA servers, topology с repl agreements |

**НЕ обслуживаем:** RHEL IdM enterprise plans / Red Hat поддержку (санкционно).

---

## 1. ПРИЁМ

```markdown
### Опросник: FreeIPA клиента

1. Версия FreeIPA: ipa --version
2. ОС под IPA: [Astra SE / РЕД ОС / Rocky / RHEL / ALT Server]
3. Realm (обычно EXAMPLE.LOCAL): _______________________
4. Domain (FQDN): _______________________
5. IPA-серверы (FQDN + IP): _______________________
6. Количество хостов (ipa host-find): ____
7. Количество пользователей (ipa user-find): ____
8. CA-режим: integrated (Dogtag) / external / без CA
9. Trust с AD настроен: да / нет
10. DNS-зоны в IPA (ipa dnszone-find): _______________________
11. Что использует IPA: [SSH auth / sudo / HBAC / automount / certificates]
12. Бэкапы: ipa-backup существует? куда сохраняется?
13. Сертификаты TLS (веб-консоль IPA) — истекают: ____.____.____
14. Кто обслуживает IPA сейчас: _______________________
```

**Красные флаги:**
- Single IPA server без реплики (vosстановление долгое)
- Не было `ipa-backup` > 30 дней
- Dogtag CA-сертификаты истекают < 60 дней (после истечения restore почти невозможен)
- Версия FreeIPA < 4.8 (устарела, много CVE)
- Закрытый firewall мешает репликации (порт 389, 636, 88, 464)

---

## 2. ПОДКЛЮЧЕНИЕ

### 2.1. Node exporter на IPA-хосты

```bash
# На каждом IPA server + replica:
sudo bash /opt/mspshield/CLIENT/node_exporter/install_linux.sh
```

### 2.2. Кастомные метрики IPA (textfile collector)

```bash
# /usr/local/bin/ipa_metrics.sh — запуск каждые 5 мин через systemd timer

#!/usr/bin/env bash
TEXTFILE=/var/lib/node_exporter/textfile_collector/ipa.prom
TMP=$(mktemp)

# Сервисы IPA должны быть running
for svc in ipa krb5kdc kadmin dirsrv@EXAMPLE-LOCAL pki-tomcatd@pki-tomcat named-pkcs11; do
  status=$(systemctl is-active "$svc" 2>/dev/null || echo "unknown")
  val=0; [[ "$status" == "active" ]] && val=1
  printf 'ipa_service_up{service="%s"} %d\n' "$svc" "$val" >> "$TMP"
done

# Количество пользователей / хостов / групп (требует kinit как admin)
USERS=$(ipa user-find --sizelimit=0 2>/dev/null | grep -c "^  User login:")
HOSTS=$(ipa host-find --sizelimit=0 2>/dev/null | grep -c "^  Host name:")
GROUPS=$(ipa group-find --sizelimit=0 2>/dev/null | grep -c "^  Group name:")
echo "ipa_users_total $USERS" >> "$TMP"
echo "ipa_hosts_total $HOSTS" >> "$TMP"
echo "ipa_groups_total $GROUPS" >> "$TMP"

# Репликация
REPL_STATUS=$(ipa-replica-manage list-ruv 2>/dev/null | grep -c "unavailable")
echo "ipa_replication_unavailable $REPL_STATUS" >> "$TMP"

# Сертификаты — дни до истечения самого раннего
MIN_DAYS=$(getcert list 2>/dev/null | grep expires | awk '{print $2" "$3" "$4}' | \
  while read D; do date -d "$D" +%s; done | sort -n | head -1 | \
  awk -v now=$(date +%s) '{print int(($1-now)/86400)}')
echo "ipa_cert_min_days_left ${MIN_DAYS:-999}" >> "$TMP"

# Размер LDAP-базы (если критичен)
LDAP_SIZE=$(du -sb /var/lib/dirsrv/slapd-*/db | head -1 | awk '{print $1}')
echo "ipa_ldap_db_bytes ${LDAP_SIZE:-0}" >> "$TMP"

mv "$TMP" "$TEXTFILE"
chmod 644 "$TEXTFILE"
```

Добавить systemd timer `ipa-metrics.timer` с OnCalendar=`*:0/5`.

### 2.3. Бэкап FreeIPA

**Ежедневный полный бэкап:**

```bash
# /usr/local/bin/ipa_backup.sh
#!/usr/bin/env bash
set -euo pipefail

DATE=$(date +%F)
BACKUP_DIR=/var/lib/ipa/backup

# 1) Нативный ipa-backup (создаёт целостный snapshot всех компонентов)
sudo ipa-backup
# → /var/lib/ipa/backup/ipa-full-YYYY-MM-DD-HH-MM-SS

# 2) Доп. экспорт в LDIF (для удобства восстановления частей)
sudo ldapsearch -LLL -x -D "cn=Directory Manager" \
  -w "$DM_PASS" -b "dc=example,dc=local" > /tmp/ldap-${DATE}.ldif
sudo gzip /tmp/ldap-${DATE}.ldif

# 3) Restic в Yandex Object Storage
restic -r s3:s3.yandexcloud.net/client-<slug>-backups backup \
  "$BACKUP_DIR" /tmp/ldap-${DATE}.ldif.gz --tag freeipa

# 4) Чистка старого
restic -r s3:... forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune

rm /tmp/ldap-*.ldif.gz
```

Запускать ежедневно в 3:00 через cron/systemd.

### 2.4. Мониторинг изменений директории (Silver+ с Loki)

```yaml
# Promtail на каждом IPA server
- job_name: freeipa_logs
  static_configs:
    - targets: [localhost]
      labels:
        job: freeipa
        __path__: /var/log/dirsrv/slapd-EXAMPLE-LOCAL/access
        __path__: /var/log/krb5kdc.log
        __path__: /var/log/httpd/error_log
```

В Grafana дашборд «FreeIPA Audit» показывает:
- Неудачные попытки Kerberos (5 преаутентфейлов/мин → алерт)
- Изменения в LDAP (add/mod/del записей)
- HBAC deny-события

---

## 3. НАСТРОЙКА алертов

```yaml
- alert: IPA_ServiceDown
  expr: ipa_service_up == 0
  for: 3m
  labels: { severity: critical, service: "freeipa" }
  annotations:
    summary: "IPA сервис {{ $labels.service }} не работает на {{ $labels.instance }}"

- alert: IPA_ReplicationBroken
  expr: ipa_replication_unavailable > 0
  for: 15m
  labels: { severity: critical, service: "freeipa" }

- alert: IPA_CertExpiringSoon
  expr: ipa_cert_min_days_left < 30
  labels: { severity: warning, service: "freeipa" }
  annotations:
    summary: "IPA сертификат истекает через {{ $value }} дней (самый близкий)"
    # Если < 7 дней — severity повышается вручную → critical

- alert: IPA_CertCritical
  expr: ipa_cert_min_days_left < 7
  labels: { severity: critical, service: "freeipa" }

- alert: IPA_LdapDbGrowingFast
  expr: increase(ipa_ldap_db_bytes[7d]) > 500 * 1024 * 1024
  labels: { severity: info, service: "freeipa" }
  annotations:
    summary: "LDAP база выросла на > 500 МБ за неделю"

- alert: IPA_BackupStale
  expr: time() - ipa_backup_last_success_ts > 86400 * 2
  labels: { severity: critical, service: "freeipa" }
```

---

## 4. КОНТРОЛЬ

### Еженедельно
- `ipactl status` — все сервисы running на каждом IPA
- `ipa-replica-manage list-ruv` — нет `unavailable`
- Неудачные Kerberos-входы (тренд)
- Статус бэкапа + тестовый restore (раз в месяц)

### Ежемесячно
- Restore drill: развернуть `ipa-backup` в изолированную VM, `ipa-server-install --setup-dns`
- Проверка `getcert list` — ни один сертификат не истекает < 60 дней
- Ревизия `ipa sudorule-find` / `ipa hbactest` — что изменилось

### Ежеквартально
- Обновление FreeIPA (`dnf/apt update --security` — пакеты freeipa-server, 389-ds-base)
- Проверка tombstones (`cn=deleted entries`), вакуум при росте
- Аудит групп и ролей, особенно `admins`

---

## 5. TROUBLESHOOTING

### 5.1. `ipa-server: service failed to start`
```
1. systemctl status ipa
   # смотрим какой из sub-сервисов отвалился

2. ipactl status
   # обычно: dirsrv / krb5kdc / named

3. Если dirsrv (389-DS) — смотрим /var/log/dirsrv/slapd-*/errors
   # типичные:
   - "server is overloaded" → нужно увеличить nsslapd-threadnumber
   - "dblayer: dbname doesn't exist" → бита база, restore из ipa-backup

4. Если krb5kdc — проверить /var/log/krb5kdc.log, /etc/krb5.conf

5. Если httpd — проверить pki-tomcatd (CA) — часто падает из-за просроченных сертов:
   getcert list | grep -i expired
```

### 5.2. Не работает kinit / SSO
```
1. На клиентской машине:
   kinit <user>
   # смотрим ошибку

2. Типичные:
   - "Cannot find KDC" → клиент не видит IPA (DNS, firewall)
   - "Client not found in Kerberos database" → user удалён/переименован
   - "Preauthentication failed" → неверный пароль или lockout

3. Проверить SRV-записи:
   dig +short SRV _kerberos._udp.example.local
   dig +short SRV _ldap._tcp.example.local

4. Убедиться, что клиент зачислен (ipa-client-install):
   cat /etc/ipa/default.conf
   klist -k /etc/krb5.keytab
```

### 5.3. Сертификаты истекли
```
CRITICAL · восстановление долгое, требует осторожности.

1. Если истёк CA — следовать официальной процедуре:
   https://freeipa.org/page/Howto/CA_certificate_renewal
   # обычно: ipa-cacert-manage renew + ipa-certupdate на всех репликах

2. Если истёк серверный — getcert resubmit -i <Request ID>

3. Если всё уже красное и pki-tomcatd не стартует:
   ipa-cert-fix        # автоматическое восстановление для некоторых кейсов

4. Эскалация к senior — это не случай для junior в одиночку!
```

### 5.4. Репликация не работает
```
1. ipa-replica-manage list-ruv
   # смотрим, какая replica "unavailable"

2. На проблемном:
   systemctl restart dirsrv@EXAMPLE-LOCAL

3. Если не помогло:
   ipa-replica-manage re-initialize --from <master-fqdn>
   # ВНИМАНИЕ: это перезальёт всю базу от master'а → все
   # изменения на реплике потеряются

4. Если replica вообще не подключается:
   ipa-replica-manage del <bad-replica> --force
   # → пересоздать реплику с нуля через ipa-replica-install
```

---

## Upsell / cross-sell

| Триггер | Предложение | Цена |
|---|---|---|
| Single IPA без replica | Развёртывание replica + trust | ADDON 30–50k₽ |
| Нет HBAC (все = всем) | Внедрение HBAC + ролевая модель | ADDON 25k₽ |
| Существующий AD хочет hybrid | Настройка AD-trust с FreeIPA | Проект 40–80k₽ |
| Старый FreeIPA 4.6 | Миграция на 4.9+ / RHEL IdM совместимый | Проект |
| Сертификаты истекают, страшно | Сопровождение renewals как услуга | Входит в Gold |

---

## Чек-лист junior: «готов принимать `FreeIPA`»

- [ ] Понимаю 5 компонентов IPA (LDAP, KDC, CA, DNS, HTTPD)
- [ ] Установил FreeIPA на учебной VM (`ipa-server-install`)
- [ ] Добавил клиента (`ipa-client-install`) и попробовал kinit/ssh
- [ ] Прошёл `ipa-backup` и `ipa-restore` в изолированной среде
- [ ] Прогнал getcert list, понимаю что такое Dogtag
- [ ] Знаю границу: мы сопровождаем, но миграцию леса делаем как PROJECT
- [ ] Умею написать правило HBAC (host-based access control)
