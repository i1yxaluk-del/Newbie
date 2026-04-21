# Сервис: Файловый сервер

> **Сложность:** ⭐⭐☆☆☆. Junior — базовый.
> **Тарифы:** Bronze (место + бэкапы), Silver (+ теневые копии, аудит).

## Варианты у клиентов

| Вариант | Доля | Особенности |
|---|---|---|
| Windows Server SMB (на DC) | 50% | NTFS ACL + AD-группы |
| Windows Server SMB (dedicated) | 25% | DFS, shadow copy |
| Samba на Astra/RHEL | 15% | Интегрирован с AD/FreeIPA |
| NAS (Synology/QNAP) | 10% | Ограниченный мониторинг |

## 1. ПРИЁМ

```markdown
1. Сервер (FQDN/IP): _______________________
2. Общие папки (shares): _______________________
3. Размер данных (ТБ): ____
4. ACL: [AD-группы / локальные / смешано]
5. Shadow Copy включен: да / нет
6. Бэкап: [средствами ОС / Veeam / restic / нет]
7. DFS: да / нет
8. Антивирус на сервере: [KES / Defender / ... / нет]
9. Последние инциденты (ransomware, потеря файлов): _______________________
```

**Красные флаги:**
- Нет shadow copy и нет бэкапа → ransomware = потеря всего
- Все юзеры имеют Modify на корень share
- Файлы старше 5 лет не архивированы (balloon)
- Нет квот → один юзер может забить весь диск

## 2. ПОДКЛЮЧЕНИЕ

### Windows
```powershell
# windows_exporter с collectors: smb, logical_disk, system
# + textfile с метриками shadow copy:
$sc = vssadmin list shadows | Select-String "Number of shadow copies"
"smb_shadow_copies_count $($sc.Count)" | Out-File ...
```

### Linux Samba
```bash
# smb_exporter (сторонний)
# или собственный scraper smbstatus → textfile
smbstatus --brief --json | jq '.locked_files | length' → smb_locked_files
```

### Бэкап
- **Windows**: wbadmin или Veeam Community → restic tail в S3
- **Linux Samba**: `rsync --backup` → restic
- **Шардинг больших (> 500 ГБ)**: инкрементальный restic (он умеет дедупликацию)

## 3. АЛЕРТЫ

```yaml
- alert: FS_DiskFull
  expr: node_filesystem_avail_bytes{mountpoint=~"/srv/.*|C:/Shares.*"} / node_filesystem_size_bytes < 0.10
  for: 15m
  labels: { severity: warning, service: "fs" }

- alert: FS_DiskCritical
  expr: node_filesystem_avail_bytes{mountpoint=~"/srv/.*|C:/Shares.*"} / node_filesystem_size_bytes < 0.03
  for: 10m
  labels: { severity: critical, service: "fs" }

- alert: FS_BackupStale
  expr: time() - fs_backup_last_success_ts > 86400 * 2
  for: 10m
  labels: { severity: critical, service: "fs" }

- alert: FS_ShadowCopyLow
  expr: smb_shadow_copies_count < 7
  for: 1h
  labels: { severity: info, service: "fs" }
  annotations:
    summary: "Shadow copy < 7 снапшотов — глубина отката малая"
```

## 4. КОНТРОЛЬ

- **Еженедельно**: свободное место, тренд роста, топ-пользователей по объёму
- **Ежемесячно**: проверка восстановления случайного файла из бэкапа
- **Ежеквартально**: ревизия ACL (чьи права давно не использовались)

## 5. TROUBLESHOOTING

### «Не могу открыть файл / долго открывается»
```
1. Проверить нагрузку на сервер (CPU, IOPS, очередь)
2. smbstatus — кто держит блокировку файла
3. В Windows: Computer Management → Shared Folders → Open Files
4. Сетевой mtu / duplex (часто 100 Mb полудуплекс после хаба)
```

### «Случайно удалили папку»
```
Порядок обзвона:
1. Shadow copy:
   Windows Explorer → Properties → Previous Versions → выбрать snapshot
2. Если shadow нет — restic restore:
   restic restore latest --target /tmp/recover --include /srv/files/Marketing
3. Если бэкапа тоже нет → перехват reclaim через undelete на блочном уровне
   (инструмент TestDisk / R-Studio — последний шанс)
4. Пост-мортем: как не повторить (ACL, обучение, предупредительный алерт)
```

## Upsell

| Триггер | Предложение | Цена |
|---|---|---|
| Диск > 80% | Расширение диска | Зависит от Yandex Cloud |
| Нет shadow copy | Включение + retention | 5k₽ |
| Файлы > 5 лет | Архивирование в S3 Cold | 15k₽ + хранилище |
| Нет ACL (все = всем) | Пересмотр + ролевая модель | 20k₽ |

## Чек-лист junior

- [ ] Умею читать ACL NTFS и в Samba (getfacl/posix)
- [ ] Настроил shadow copy на Windows
- [ ] Выполнил рестор из restic в тестовой среде
- [ ] Знаю ограничения NAS — где мы можем, а где нет
