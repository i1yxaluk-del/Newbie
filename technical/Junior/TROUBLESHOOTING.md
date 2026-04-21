# Troubleshooting Playbook

> Библиотека «что делать, если...». Junior в сложной ситуации открывает этот файл
> и ищет свой алерт по тегу. Каждый runbook — 5 шагов, не больше.

## Навигация по алертам

| Тег / алерт | Runbook |
|---|---|
| `InstanceDown` / `up == 0` | [§1.1](#11-instance-down-хост-не-отвечает) |
| `DiskFillingFast` | [§1.2](#12-диск-заполняется-быстро) |
| `DiskCriticallyFull` (< 5%) | [§1.3](#13-диск-почти-полный--3-5) |
| `HighCPU` / `HighLoadAverage` | [§1.4](#14-высокая-загрузка-cpu) |
| `OutOfMemory` / `NodeMemoryUsage` | [§1.5](#15-нехватка-памяти) |
| `WebsiteDown` / `probe_success == 0` | [§2.1](#21-сайт-не-отвечает) |
| `SslExpiringSoon` | [§2.2](#22-ssl-сертификат-истекает) |
| `OneC_ServerDown` / `OneC_LicenseLost` | [§3.1](#31-1с-сервер-упал) |
| `OneC_SlowQueriesSurge` | [§3.2](#32-1с-тормозит) |
| `AD_DC_Down` / `AD_ReplicationFailure` | [§4.1](#41-ad-dc-упал-или-репликация) |
| `AD_MassLockout` | [§4.2](#42-массовый-lockout-в-ad) |
| `IPA_ServiceDown` / `IPA_ReplicationBroken` | [§5.1](#51-freeipa-сервис-упал) |
| `IPA_CertExpiringSoon` / `IPA_CertCritical` | [§5.2](#52-сертификаты-freeipa-истекают) |
| `Mail_Unreachable` / `Mail_IP_Blacklisted` | [§6.1](#61-почта-не-работает) |
| `DB_Down` / `DB_ReplicationLagHigh` | [§7.1](#71-бд-не-отвечает) |
| `Backup_Failed` / `*_BackupStale` | [§8.1](#81-бэкап-не-выполняется) |
| `Alertmanager_NotNotifying` (наш мониторинг) | [§9.1](#91-у-нас-сломался-мониторинг) |

---

## 1. ХОСТ (общие)

### 1.1. Instance down (хост не отвечает)
```
1. Проверить сеть: ping, traceroute, test-netconnection <port>
2. Из Bastion: ssh <host> — если не пускает, пробовать через Yandex Cloud console
3. Проверить VM в Yandex Cloud (возможно, остановлена, OOM, failover)
4. Запустить recovery последовательность:
   - Stuck? Hard-reset через API Yandex Cloud
   - Сеть? Рестарт wireguard: sudo systemctl restart wg-quick@wg0
5. Эскалация клиенту (SLA-часы) + senior-инженеру при необходимости.
```

### 1.2. Диск заполняется быстро
```
1. df -h; du -sh /var/* /home/* | sort -h
2. Найти топ файлы: find / -size +1G -type f 2>/dev/null
3. Типичные виновники:
   - /var/log забит (logrotate сломан?) → очистка + reinit
   - /var/lib/docker (orphaned images) → docker system prune -af
   - /var/lib/mysql или postgres — бэкапы не чистятся
4. Если не можем очистить — Yandex Cloud: увеличить диск online (resize)
5. Алерт DiskFillingFast — превратить в тикет «оптимизация места» (upsell)
```

### 1.3. Диск почти полный (< 3-5%)
```
CRITICAL! Сначала действия, потом мышление:
1. docker system prune -af --volumes        (если есть docker)
2. journalctl --vacuum-time=1d              (1 день истории журналов — ок)
3. rm /var/cache/apt/archives/*.deb
4. Удалить старые бэкапы локально (их копия в S3 есть)
5. Если всё ещё нет места — resize в Yandex Cloud (занимает ~5 минут)
```

### 1.4. Высокая загрузка CPU
```
1. top -H  (потоки)  или  htop (если стоит)
2. pidstat -p ALL 5  (кто пик)
3. Частые случаи:
   - ragent/rphost (1С) — смотреть 1С
   - kswapd — на самом деле проблема памяти, не CPU
   - mysqld/postgres — долгий запрос
4. Нагрузка > 15 минут — если клиент бизнес-критичный, уведомить + план миграции ресурсов (ADDON)
```

### 1.5. Нехватка памяти
```
1. free -m; ps aux --sort=-%mem | head
2. OOM-killer уже сработал? dmesg | grep -i "killed process"
3. Меры:
   - Рестарт сервиса с утечкой
   - Увеличить swap (sysctl swappiness)
   - ADDON: увеличение RAM у VM в Yandex Cloud
```

---

## 2. САЙТ

### 2.1. Сайт не отвечает
См. [`../0_Common/SERVICES/website.md#51-алерт-websitedown`](../0_Common/SERVICES/website.md)

### 2.2. SSL сертификат истекает
См. [`../0_Common/SERVICES/website.md#53-алерт-sslexpiringsoon`](../0_Common/SERVICES/website.md)

---

## 3. 1С

### 3.1. 1С сервер упал
См. [`../0_Common/SERVICES/1c_server.md#51-сервер-1с-не-запускается`](../0_Common/SERVICES/1c_server.md)

### 3.2. 1С тормозит
См. [`../0_Common/SERVICES/1c_server.md#52-1с-тормозит-универсальная-жалоба`](../0_Common/SERVICES/1c_server.md)

---

## 4. Active Directory

### 4.1. AD DC упал или репликация
См. [`../0_Common/SERVICES/ad_domain.md#51-dc-не-отвечает-ad_dc_down`](../0_Common/SERVICES/ad_domain.md)

### 4.2. Массовый lockout в AD
См. [`../0_Common/SERVICES/ad_domain.md#53-массовые-локауты-ad_masslockout`](../0_Common/SERVICES/ad_domain.md)

---

## 5. FreeIPA

### 5.1. FreeIPA сервис упал
См. [`../0_Common/SERVICES/freeipa_domain.md#51-ipa-server-service-failed-to-start`](../0_Common/SERVICES/freeipa_domain.md)

### 5.2. Сертификаты FreeIPA истекают
```
CRITICAL-территория · junior обязан позвать senior.
См. `../0_Common/SERVICES/freeipa_domain.md` §5.3.
```

---

## 6. Почта / DNS

### 6.1. Почта не работает
См. [`../0_Common/SERVICES/mail_dns.md`](../0_Common/SERVICES/mail_dns.md)

---

## 7. БД

### 7.1. БД не отвечает
См. [`../0_Common/SERVICES/database.md`](../0_Common/SERVICES/database.md)

---

## 8. Бэкапы

### 8.1. Бэкап не выполняется
```
1. Смотреть логи systemd timer:
   journalctl -u <client>_backup.timer -n 50
   journalctl -u <client>_backup.service -n 50

2. Частые причины:
   - Пароль restic не в keystore → восстановить из Vault
   - S3 креды просрочены → обновить в Yandex Cloud
   - Нет сети до s3.yandexcloud.net → проверить wireguard
   - Место закончилось на исходном (что-то хотим скопировать но source недоступен)

3. Выполнить вручную: bash /opt/mspshield/backups/<client>.sh
4. Если восстановлено — добавить test_snapshot в comment для weekly-report
```

---

## 9. Наш мониторинг

### 9.1. У нас сломался мониторинг
```
Мета-проблема: Prometheus/Alertmanager/Grafana на Monitoring VM умерли.

1. Мы узнаём об этом через Blackbox-внешний (от второго регионального VM)
   или через дедмен (dead-man-switch) в Alertmanager.

2. Проверить Monitoring VM:
   ssh monitor-vm
   docker compose ps
   docker compose logs --tail 100 | grep -i error

3. Часто — забит диск (см. §1.3)
4. Если VM упала — переключиться на standby region (Yandex Cloud):
   terraform apply -var="active_region=ru-central1-b"

5. Post-mortem — обязательно, потому что если падает наш мониторинг,
   клиенты в этот момент не защищены.
```

---

## Универсальные правила junior

1. **Не паниковать.** Сперва прочитать алерт до конца.
2. **Не лезть в прод с правами write**, пока не обсудил с senior.
3. **Документировать в тикете** каждый шаг — что сделал, что увидел.
4. **Эскалация — это НЕ слабость.** Это профессионализм.
5. **После инцидента — пост-мортем** в Notion, даже если junior сам справился.
6. **Если не понял — спрашиваешь.** В чате команды, без стыда.
