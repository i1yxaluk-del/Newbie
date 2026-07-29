# Миграция MSP Cloud на новый аккаунт Yandex Cloud

> Перенос сайта `msp-claude.online` и всех сервисов со старого аккаунта (грант кончился) на новый (с грантом).

## Что переносится

| Компонент | Данные | Размер |
|-----------|--------|--------|
| MongoDB | 10 leads (база заявок) | 1.8 KB |
| Stalwart Mail | конфиг + почтовые ящики | 2.4 MB |
| Vaultwarden | хранилище паролей | 173 KB |
| Caddy | SSL-сертификаты Let's Encrypt | 14 KB |
| Restic | конфиг бэкапов (S3 keys, скрипт) | ~5 KB |
| Secrets | backend/.env, deploy/.env | ~1 KB |

**Итого: ~2.6 MB** — всё помещается в один SCP-трансфер.

## Архитектура (что работает на ВМ)

```
Caddy (systemd) ─── HTTPS, reverse proxy
  ├── msp-claude.online      → /var/www/landing (статика) + /api/ → :8001
  ├── vault.msp-claude.online → Vaultwarden :8180
  ├── mon.msp-claude.online   → Grafana :3000
  └── mail.msp-claude.online  → cert для Stalwart

Docker Compose "msp":
  ├── mongo:7.0          — БД заявок
  ├── backend (FastAPI)  — API лендинга, интеграции (Kaiten, Telegram, MAX)
  ├── stalwart:v0.16     — почта (relay через Yandex Postbox :465)
  └── vaultwarden        — менеджер паролей

Docker Compose "monitoring":
  ├── prometheus, alertmanager, grafana
  ├── node-exporter, cadvisor, blackbox
  └── telegram-webhook, max-alerter

Restic (systemd timer, 02:00 daily):
  └── бэкап → S3 (mspshield-backups-prod)
```

## Пошаговая миграция

### Шаг 0. Подготовка (уже сделано ✓)

- [x] ВМ запущена, данные выкачаны в `migration/`
- [x] `mongodump.archive.gz` — дамп MongoDB
- [x] `stalwart-*.tar.gz` — почта
- [x] `vaultwarden-data.tar.gz` — пароли
- [x] `caddy-data.tar.gz` — SSL
- [x] `backend.env.bak` / `deploy.env.bak` — секреты
- [x] `restic-*.sh` — бэкапы

### Шаг 1. Привязать новый аккаунт YC

```powershell
yc config profile create msp-new
yc config profile activate msp-new
yc init
# Выбрать новый аккаунт (с грантом) → облако → folder
```

Проверка:
```powershell
yc resource-manager cloud list
# Должно быть новое облако
```

### Шаг 2. Создать ВМ (deploy.ps1)

```powershell
cd deploy\yandex
.\deploy.ps1 -Domain msp-claude.online -Preemptible $true -UseStaticIp $true
```

Скрипт:
- Создаст folder, VPC, subnet, security group
- Создаст ВМ (2 vCPU / 4 GB / 50 GB SSD, preemptible)
- Зарезервирует static IP
- Загрузит код, соберёт frontend, запустит docker
- Выведет **новый IP** ← запомнить!

Время: ~8-12 минут.

### Шаг 3. Перенести данные (migrate.ps1)

```powershell
cd migration
.\migrate.ps1 -NewVmIp <IP_из_шага_2>
```

Скрипт:
- Загрузит все файлы из `migration/` на ВМ
- Остановит контейнеры
- Восстановит MongoDB, Stalwart, Vaultwarden, Caddy, restic
- Перезапустит всё
- Проверит healthcheck

Время: ~2-3 минуты.

### Шаг 4. Обновить DNS

В панели регистратора (reg.ru):

| Тип | Имя | Значение | TTL |
|-----|-----|----------|-----|
| A | @ | `<новый_IP>` | 300 |
| A | www | `<новый_IP>` | 300 |
| A | mail | `<новый_IP>` | 300 |
| A | vault | `<новый_IP>` | 300 |
| A | mon | `<новый_IP>` | 300 |
| MX | @ | mail.msp-claude.online (10) | 300 |

Ожидание: 5-30 минут.

### Шаг 5. Проверка

```powershell
# Сайт
curl https://msp-claude.online/api/health
# → {"status":"ok"}

# Форма заявки
curl -X POST https://msp-claude.online/api/leads -H "Content-Type: application/json" -d '{"name":"Тест","phone":"+79990000000","email":"t@t.ru","company":"Тест","tier":"bronze","consent":true,"website":""}'

# Почта (SSH tunnel)
ssh -L 8080:127.0.0.1:8080 ubuntu@<IP>
# → http://localhost:8080/admin

# Vaultwarden
# → https://vault.msp-claude.online

# Grafana
# → https://mon.msp-claude.online
```

### Шаг 6. Остановить старую ВМ

```powershell
yc config profile activate default  # старый профиль
yc compute instance stop fhmab2qg10esn09j0na2 --folder-id b1gd6dph0a4cnds0heel
# Через 7 дней, если всё ок:
yc compute instance delete fhmab2qg10esn09j0na2 --folder-id b1gd6dph0a4cnds0heel
```

## Откат (если что-то пошло не так)

1. DNS вернуть на старый IP `93.77.184.219`
2. Запустить старую ВМ: `yc compute instance start fhmab2qg10esn09j0na2 --folder-id b1gd6dph0a4cnds0heel`
3. Данные на старой ВМ не тронуты (мы только читали)

## Файлы в этой папке

| Файл | Назначение | Коммитить? |
|------|-----------|------------|
| `migrate.ps1` | Оркестратор миграции | ✅ да |
| `restore-on-vm.sh` | Скрипт восстановления на ВМ | ✅ да |
| `README.md` | Эта инструкция | ✅ да |
| `mongodump.archive.gz` | Дамп MongoDB | ❌ нет (данные) |
| `*.tar.gz` | Дампы volumes | ❌ нет (данные) |
| `*.env.bak` | Секреты | ❌ нет (секреты!) |
| `restic-env.sh` | Ключи S3 | ❌ нет (секреты!) |

## Замечания

- **Static IP**: deploy.ps1 резервирует static IP (+189₽/мес). Без него preemptible-ВМ меняет IP при рестарте → DNS ломается.
- **Postbox**: SMTP-релей через `postbox.cloud.yandex.net:465`. Ключи в backend.env.bak. Если Postbox привязан к старому аккаунту — нужно пересоздать API key в новом.
- **Object Storage**: бакет `mspshield-backups-prod` в старом облаке. Restic будет писать туда же (ключи в restic-env.sh). Если нужно перенести бэкапы — создать бакет в новом облаке и обновить restic-env.sh.
- **AmneziaWG**: не переносится (нет активных тенантов). Если понадобится — настроить заново по `technical/0_Common/amneziawg/`.
