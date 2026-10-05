# Cloud.ru Evolution — миграция MSPShield (итог)

**Статус: миграция выполнена — сайт работает на новом сервере cloud.ru.**

## Публичный доступ

| Что | Значение |
|---|---|
| **Постоянный IP** | **`45.132.176.143`** (direct-IP интерфейс `enp8s0`) |
| DNS A-записи | `msp-claude.online`, `www`, `mon`, `mail`, `vault` → `45.132.176.143` |
| TLS | Let's Encrypt выпущен для всех доменов ✓ |
| Лендинг | https://msp-claude.online → **200** |
| API | https://msp-claude.online/api/health → `{"status":"ok","db":"connected"}` |
| Grafana | https://mon.msp-claude.online → **200** |
| Vaultwarden | https://vault.msp-claude.online → **200** |
| Почта (sнаружи) | SMTPS `465`, IMAPS `993`, ManageSieve `4190` — OPEN |
| SSH | `ssh -i ~/.ssh/id_ed25519_yc_new ubuntu@45.132.176.143` ✓ |

## Ресурсы (cloud.ru Evolution)

| Ресурс | ID | Детали |
|---|---|---|
| **VM msp-cloud-vm** | `daf8cc7a-7a28-473e-9891-d4f3e3464b8f` | 2 vCPU / 4 GB, Ubuntu 22.04, running |
| Диск msp-boot-disk | `ccfc4a27-d435-4018-b1c6-12ce5eda0d9f` | 30 GB SSD, bootable |
| Интерфейс (внутр.) | `6b5757f5-6c5d-4cff-9b6d-1c21a8d75935` | `10.0.0.6` (enp3s0), regular |
| Интерфейс (direct-IP) | `ca4c083a-94a5-4ee2-a89e-05dd43ccd265` | `45.132.176.143` (enp8s0) |
| Floating IP | `f1aa6c2f-92ee-4431-866e-e3b3208da173` | `45.132.176.143` (привязан к direct-IP интерфейсу) |
| Сабнет | `f407a936-4b87-4858-b100-72912a737877` | `Default_ru.AZ-3`, 10.0.0.0/24 |
| Security Group | `5dc08e55-6819-4e23-92ad-47f18cb61b6a` | `SSH-access_ru.AZ-3` (19 ingress-правил) |
| Зона / Флавор / Образ | `2c63c482…` / `82d31572…` (lowcost10-2-4) / `474c9e98…` (ubuntu-22.04) | ru.AZ-3 |
| Проект | `e39dc535-25e8-4d64-9572-885b08a1f37e` | «Новый Проект» |

## ⚠️ Ключевой нюанс: маршрутизация двух интерфейсов

ВМ имеет 2 интерфейса: `enp3s0` (внутр. 10.0.0.6) и `enp8s0` (direct-IP 45.132.176.143).
Оба получают default-маршрут с **одинаковой metric 100** → ответные пакеты (включая
от docker-контейнеров) уходят через `enp3s0` с чужим source-IP → **соединения рвутся**
(SSH/HTTP таймаутят, почтовые порты недоступны).

**Решение** (применено, персистентно): добавить в основную таблицу default через `enp8s0`
с **metric 50** (приоритетнее DHCP-шных). Внутренние маршруты (docker-бриджи, 10.0.0.0/24)
остаются в основной таблице, поэтому связь host↔контейнер не страдает.

```bash
ip route replace default via 45.132.176.1 dev enp8s0 metric 50
```

Персистентность: `/etc/systemd/system/msp-policy-route.service` (enabled) —
скрипт [`cloudru-fix-routing.sh`](cloudru-fix-routing.sh).

## Что сделано

1. ВМ + диск + интерфейсы + публичный IP созданы через API cloud.ru Evolution.
2. Security Group: открыты 80/443/443udp, 465/587/143/993/4190, 3478/5349, 4222, 49160-49250/udp.
3. Bootstrap ВМ ([`cloudru-bootstrap.sh`](cloudru-bootstrap.sh)): Docker 29.8.2, Compose v5.6.0, Caddy 2.11.7, Node 20.20.2, restic, ufw.
4. Код в `/opt/msp/Newbie` (HEAD = origin/main), env-файлы (Kaiten/Telegram/Postbox перенесены), `preflight.sh --fix` → PRE-FLIGHT OK.
5. Восстановлено из локального кита: mongo (10 лидов), vaultwarden-data, stalwart-etc, stalwart-data, stalwart.
6. Стек healthy: mongo, backend, vaultwarden, stalwart + prometheus, grafana, alertmanager, max-alerter, blackbox, cadvisor, node-exporter.
7. Фронт собран, webroot `/var/www/landing`, Caddy с боевым Caddyfile, TLS выпущен.
8. Интеграции: kaiten ✓, telegram ✓, alertmanager ✓.

## Остаётся

1. **restic на cloud.ru S3** — нужны **S3-статические ключи** Object Storage (OAuth-ключи API дают `InvalidAccessKeyId`) + имя бакета. Затем `/etc/restic/env.sh`, `restic init`, таймер.
2. **AmneziaWG** — `migration/awg-admin.conf` (обновить `Endpoint` на `45.132.176.143`), поднять `awg-quick@awg0`, ufw `443/udp`.
3. **MAX** — `docker exec -it msp-max-alerter python -m max_alerter.auth --authorize` (в ките не было `max-session.tar.gz`).
4. **Jami/JAMS** — восстановить из restic или пересобрать по `docs/deployment/JAMS_SETUP.md` (для этого нужны A-записи `m.`, `dht.`, `turn.`, `names.`, `invite.`, `push.` → `45.132.176.143`).
5. Порт `587`/`143` (STARTTLS) снаружи фильтруется облаком — клиенты используют `465`/`993`.
6. Удалить старую ВМ после периода наблюдения.

## Формат API cloud.ru Evolution

- **Токен:** `POST https://iam.api.cloud.ru/api/v1/auth/token`, тело `{"keyId":"…","secret":"…"}` → `access_token` (Bearer, TTL 3600 c).
- **Compute:** `https://compute.api.cloud.ru/api/v1/{vms|disks|interfaces|floating-ips|security-groups|subnets|flavors|images|disk-types}` + `?project_id=<pid>`.
- **Создание ВМ:** `POST /vms` (тело — **массив**) `[{project_id,name,availability_zone_id,flavor_id,disks:[{disk_id}],image_metadata:{public_key,name,hostname}}]`.
- **Правила SG:** `POST /security-groups/{id}/rules` `{direction,ether_type,ip_protocol,port_range,remote_ip_prefix,description}`.
- **Floating IP:** `POST /floating-ips` → `PUT /floating-ips/{id}` `{interface_id}`.
- **S3:** endpoint `s3.cloud.ru`, регион `ru-central-1`.
