# Сервис: Active Directory (Windows)

> **Сложность:** ⭐⭐⭐☆☆. Junior — после L2 (Silver-уровень).
> **Тарифы:** мониторинг на Silver, полное управление (GPO, учётки) — Silver/Gold.
> **Критичность:** **КРИТИЧЕСКАЯ** — падение AD = неработающая аутентификация у всех.

## Что такое AD для MSPShield

AD у клиента — это:
- **Домен-контроллер(ы)** (`DC`) — Windows Server 2016/2019/2022
- **DNS** — всегда на том же сервере
- **Групповые политики (GPO)** — централизованное управление
- **Файловый сервер + права** на базе AD-групп
- **Репликация** между DC (если ≥ 2)

## Типовые инсталляции

| Размер | DC | Репликация | Что обслуживаем |
|---|---|---|---|
| Малый (< 30 юзеров) | 1 DC | — | Бэкап SYSVOL, мониторинг |
| Средний (30–150) | 2 DC | LAN | Мониторинг, репликация, GPO-baseline |
| Крупный (> 150) | 3+ DC | multi-site | Site-replication, FSMO-ролей контроль |

**Мы не обслуживаем** Azure AD / Microsoft Entra (clients work directly with Microsoft).

---

## 1. ПРИЁМ

```markdown
### Опросник: AD клиента

1. Имя домена (FQDN): _______________________.local
2. NetBIOS имя: _______________________
3. Уровень функц. леса / домена: [2008R2 / 2012R2 / 2016 / 2019 / 2022]
4. Количество DC: ___  (пример: DC01, DC02)
5. IP-адреса DC (и какой PDC Emulator): _______________________
6. Где хранится SYSVOL: _______________________
7. Резервные копии AD: [System State / Windows Backup / Veeam / нет]
8. Частота бэкапа SYSVOL и NTDS.dit: ежедневно / реже
9. GPO — кто создаёт и меняет: [админ клиента / подрядчик / никто уже год]
10. Есть ли trust с другими доменами: да / нет
11. FSMO-роли — на каком DC (Schema Master, PDC и т.д.): _______________________
12. DFS / DFS-R используется: да (где) / нет
13. Уровень безопасности (password policy, lockout, AdminSDHolder): стандарт/усилен
14. LAPS (Local Admin Password Solution) внедрён: да / нет
```

**Красные флаги:**
- 1 DC без резерва — single point of failure
- System State backup отключен
- AdminSDHolder не проверялся > 12 месяцев
- В Domain Admins более 5 человек
- Пароли пользователей не меняются > 365 дней
- Включена NTLMv1 или LM-хэши

---

## 2. ПОДКЛЮЧЕНИЕ

### 2.1. Мониторинг-агент

```powershell
# На каждом DC — windows_exporter с textfile collector + AD-специфичные метрики

Invoke-WebRequest -Uri https://msp-claude.online/install/windows_exporter_dc.ps1 -OutFile dc_install.ps1
powershell -ExecutionPolicy Bypass -File dc_install.ps1

# Скрипт:
# - Ставит windows_exporter с collectors: iis, os, service, cpu, net, dns, ad
# - Настраивает textfile_inputs.d для кастомных метрик (репликация, dcdiag)
```

### 2.2. Кастомные метрики AD (textfile)

Раз в 5 минут через Task Scheduler скрипт `ad_metrics.ps1`:

```powershell
# C:\Program Files\windows_exporter\textfile_inputs\ad_metrics.prom
# Записывает:

# Статус репликации между DC
$repl = Repadmin /replsummary | Select-String "fails"
"ad_replication_failures $($repl.Count)" | Out-File -Encoding ASCII $file

# Количество FSMO-ролей на этом DC
$fsmo = (netdom query fsmo).Count
"ad_fsmo_roles_here $fsmo" | Out-File -Append -Encoding ASCII $file

# dcdiag критичные тесты
$dcdiag = (dcdiag /test:replications /test:topology /e) -match "failed"
"ad_dcdiag_failures $($dcdiag.Count)" | Out-File -Append -Encoding ASCII $file

# Размер SYSVOL и NTDS
$sysvol = (Get-Item C:\Windows\SYSVOL).Length
"ad_sysvol_bytes $sysvol" | Out-File -Append -Encoding ASCII $file

# Дни до истечения пароля krbtgt
$krbtgt = (Get-ADUser krbtgt -Properties PasswordLastSet).PasswordLastSet
$days = (New-TimeSpan -Start $krbtgt -End (Get-Date)).Days
"ad_krbtgt_password_age_days $days" | Out-File -Append -Encoding ASCII $file

# Количество локаутов за последние 24ч
$locked = Search-ADAccount -LockedOut | Measure-Object
"ad_locked_accounts $($locked.Count)" | Out-File -Append -Encoding ASCII $file
```

### 2.3. Бэкап AD

**System State backup через wbadmin + restic:**

```powershell
# C:\Scripts\ad_backup.ps1
$DATE = Get-Date -Format "yyyy-MM-dd"
$TMP  = "D:\ad-backups"

# System State (содержит NTDS.dit, SYSVOL, реестр, IIS, certificates)
wbadmin start systemstatebackup -backuptarget:$TMP -quiet

# Дополнительно — NTDS.dit snapshot через ntdsutil (offline-читабельный)
ntdsutil "activate instance ntds" snapshot create quit quit

# Restic в облако
& "C:\restic\restic.exe" -r s3:s3.yandexcloud.net/client-<slug>-backups backup $TMP --tag ad

# Очистка локально, чтобы не забить диск
Get-ChildItem $TMP -Directory | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-3) } | Remove-Item -Recurse
```

Запускать ежедневно в 2:00 (Task Scheduler).

### 2.4. GPO-baseline (Silver+)

Разворачиваем эталонный набор GPO через `technical/2_Silver/CLIENT/ad_management/gpo_baseline.ps1`:
- **Password Policy**: min 12 символов, complexity, history 24, max age 90 дней
- **Account Lockout**: 5 попыток, lockout 15 мин, counter reset 15 мин
- **Audit Policy**: logon events, object access, policy change, privilege use
- **Screen Lock**: 10 мин неактивности (для всех)
- **Restrict NTLMv1** (реестр LmCompatibilityLevel=5)
- **LAPS**: развернуть в каждом OU

После применения — бэкап каждой GPO в Git:

```powershell
Get-GPO -All | ForEach-Object {
  Backup-GPO -Name $_.DisplayName -Path D:\gpo-backups\$(Get-Date -Format yyyy-MM-dd)
}
# И коммит в наш Git-репозиторий клиента:
cd D:\gpo-backups
git add . ; git commit -m "gpo snapshot $(Get-Date -Format yyyy-MM-dd)" ; git push
```

---

## 3. НАСТРОЙКА алертов

```yaml
- alert: AD_DC_Down
  expr: up{job="windows_exporter", hostname=~".*-dc-.*"} == 0
  for: 3m
  labels: { severity: critical, service: "ad" }
  annotations:
    summary: "DC {{ $labels.hostname }} недоступен"
    runbook: "https://wiki.mspshield/runbooks/ad-dc-down"

- alert: AD_ReplicationFailure
  expr: ad_replication_failures > 0
  for: 15m
  labels: { severity: critical, service: "ad" }
  annotations:
    summary: "Репликация AD падает между DC"

- alert: AD_DCDiagFailures
  expr: ad_dcdiag_failures > 0
  for: 30m
  labels: { severity: warning, service: "ad" }

- alert: AD_KrbtgtPasswordOld
  expr: ad_krbtgt_password_age_days > 365
  labels: { severity: warning, service: "ad" }
  annotations:
    summary: "krbtgt не менялся больше года — время ротации (2× Reset-KrbPasswordSecret)"

- alert: AD_MassLockout
  expr: ad_locked_accounts > 10
  for: 10m
  labels: { severity: warning, service: "ad" }
  annotations:
    summary: "> 10 заблокированных аккаунтов — возможен brute force"

- alert: AD_NoBackup48h
  expr: time() - ad_backup_last_success_ts > 86400 * 2
  for: 10m
  labels: { severity: critical, service: "ad" }
```

---

## 4. КОНТРОЛЬ

### Еженедельно (автоматом в weekly_report.sh):
- dcdiag /test:replications — все DC pass
- repadmin /replsummary — 0 failures
- Список заблокированных аккаунтов (если > 3 — разбираем)
- Изменённые GPO за неделю (должны быть только через наш процесс)

### Ежемесячно:
- Проверка FSMO-ролей (netdom query fsmo)
- Обзор членства Domain Admins / Enterprise Admins (должно быть < 5)
- Пользователи без входа > 90 дней → предложить отключить
- Проверка LAPS-паролей (ротация каждые 30 дней)

### Ежеквартально:
- **Ротация krbtgt** (2 раза с интервалом 24ч)
- Проверка AdminSDHolder
- Тестовое восстановление System State в изолированной VM
- Аудит групп и прав доступа (Silver+)

---

## 5. TROUBLESHOOTING

### 5.1. DC не отвечает (AD_DC_Down)
```
1. Ping, RDP, Network:
   Test-NetConnection <dc-ip> -Port 389

2. Если сеть есть, но LDAP не отвечает:
   Get-Service NTDS, DNS, KDC, Netlogon | Format-Table Name, Status
   # Запустить остановленные

3. Journaling:
   Get-EventLog -LogName "Directory Service" -Newest 50
   Get-EventLog -LogName System -Newest 50 | Where-Object EntryType -eq "Error"

4. Если второй DC доступен — изолировать проблемный, передать FSMO-роли:
   netdom query fsmo
   # Если все FSMO на упавшем — Seize на здоровом:
   ntdsutil > roles > connections > connect to server <healthy-dc>
   > quit > seize rid master ... (по очереди)

5. Эскалация клиенту при:
   - Повреждении NTDS.dit (нужен restore из бэкапа)
   - Физическом отказе DC (нужна замена железа)
```

### 5.2. Репликация не работает
```
1. repadmin /showrepl <dc-name>
2. repadmin /syncall /A /e    # принудительная синхронизация
3. Если ошибка «access denied» — проблема в SPN, решается netdom resetpwd
4. Если ошибка «DNS lookup» — проверить, что DC видит себя через nslookup
5. Если SYSVOL не реплицируется (FRS/DFSR) — D4/D2 процедура:
   # Подробнее: https://docs.microsoft.com/.../dfsr-non-authoritative-restore
```

### 5.3. Массовые локауты (AD_MassLockout)
```
1. Event Viewer → Security → Event ID 4740 — откуда идёт блокировка
2. LockoutStatus.exe для конкретного юзера
3. Частые источники:
   - Сохранённый старый пароль в RDP на чужом ПК
   - Служба, запущенная от имени юзера с просроченным паролем
   - Почтовый клиент на телефоне (!)
   - Реальный brute-force (блок IP на firewall)
4. В Wazuh (Gold) уже есть правило detection → pagerduty
```

### 5.4. GPO не применяется
```
1. На клиентской машине:
   gpresult /h report.html /scope computer
   # или gpresult /r /scope user

2. Проверить что нужная OU имеет linked GPO
3. Проверить права применения (Security Filtering в GPMC)
4. Принудительно:
   gpupdate /force
5. Если GPO «пропала» — восстановить из Git:
   cd D:\gpo-backups\<date> ; Restore-GPO -All -Path .
```

---

## Upsell / cross-sell

| Триггер | Предложение | Цена |
|---|---|---|
| 1 DC, без резерва | Развёртывание secondary DC | ADDON 35k₽ + лицензия Windows |
| Нет LAPS | Внедрение LAPS + обучение | ADDON 15k₽ |
| ≥ 100 юзеров без Azure | Hybrid-setup с Azure Connect | Проект |
| Требования ФСТЭК | Аудит и hardening AD | Требует Gold + ADDON |
| Миграция старого AD 2008R2 | Повышение уровня леса + миграция | Проект 80–150k₽ |

---

## Чек-лист junior: «готов принимать `AD`»

- [ ] Знаю разницу AD / Azure AD / hybrid
- [ ] Прогнал dcdiag и repadmin на учебном стенде, понимаю что «pass»/«fail»
- [ ] Развернул GPO-baseline из нашего скрипта
- [ ] Сделал System State backup + тестовый restore в VM
- [ ] Знаю последовательность ротации krbtgt (и почему 2 раза)
- [ ] Умею читать Security-журналы и находить lockout-источник
- [ ] Понимаю ответственность: MSPShield = мониторинг + GPO-baseline + бэкап.
      Миграцию/апгрейд леса — только через ADDON и с привлечением senior.
