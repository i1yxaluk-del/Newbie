# РњРёРіСЂР°С†РёСЏ MSPShield в†’ Cloud.ru Evolution

РџРµСЂРµРЅРѕСЃ production СЃРѕ single-VM Yandex Cloud РЅР° Cloud.ru Evolution.
РљР°РЅРѕРЅРёС‡РµСЃРєРёР№ РїРѕСЂСЏРґРѕРє Рё gates вЂ” [`./README.md`](README.md) Рё [`../docs/deployment/MIGRATION_RUNBOOK.md`](../docs/deployment/MIGRATION_RUNBOOK.md).
Р—РґРµСЃСЊ вЂ” С‚РѕР»СЊРєРѕ РѕС‚Р»РёС‡РёСЏ РґР»СЏ Cloud.ru Рё Р°РґР°РїС‚РёСЂРѕРІР°РЅРЅС‹Рµ РєРѕРјР°РЅРґС‹.

## РР·РІРµСЃС‚РЅС‹Рµ С„Р°РєС‚С‹ (РёСЃС…РѕРґРЅС‹Рµ РґР°РЅРЅС‹Рµ)

| РџРѕР»Рµ | Р—РЅР°С‡РµРЅРёРµ |
|---|---|
| РќРѕРІР°СЏ Р’Рњ | `vm-971aab`, Р·РѕРЅР° `ru.AZ-3`, СЃС‚Р°С‚СѓСЃ В«Р—Р°РїСѓСЃРєР°РµС‚СЃСЏВ» |
| РџСѓР±Р»РёС‡РЅС‹Р№ IP | `45.132.177.214` |
| Р’РЅСѓС‚СЂРµРЅРЅРёР№ IP | `10.0.0.5` |
| Security group | `Default` |
| S3-РєР»СЋС‡Рё (restic-Р±СЌРєР°Рї) | Key ID + Key Secret (РёР· РєРѕРЅСЃРѕР»Рё Cloud.ru Object Storage) |
| DNS A-Р·Р°РїРёСЃРё | СѓР¶Рµ РїСЂРѕРїРёСЃР°РЅС‹ (РїСЂРѕРІРµСЂРёС‚СЊ С„Р°РєС‚РёС‡РµСЃРєРёРµ Р·РЅР°С‡РµРЅРёСЏ РїРµСЂРµРґ switch) |

Р›РѕРєР°Р»СЊРЅС‹Р№ Р±СЌРєР°Рї-РєРёС‚ РІ [`migration/`](.) :
`mongodump.archive.gz`, `vaultwarden-data.tar.gz`, `stalwart-etc.tar.gz`,
`stalwart-data.tar.gz`, `caddy-data.tar.gz`, `backend.env.bak`, `deploy.env.bak`,
`awg-admin.conf`, `restic-env.sh`, `restic-excludes.txt`.

РћС‚СЃСѓС‚СЃС‚РІСѓРµС‚ `max-session.tar.gz` в†’ MAX-СЃРµСЃСЃРёСЏ РїРѕС‚СЂРµР±СѓРµС‚ СЂСѓС‡РЅРѕР№ Р°РІС‚РѕСЂРёР·Р°С†РёРё
(`docker exec -it msp-max-alerter python -m max_alerter.auth --authorize`) вЂ” СЌС‚Рѕ С€С‚Р°С‚РЅРѕ.

## Р§РµРј Cloud.ru РѕС‚Р»РёС‡Р°РµС‚СЃСЏ РѕС‚ Yandex Cloud

- **РќРµС‚ `yc`-CLI.** РЈРїСЂР°РІР»РµРЅРёРµ вЂ” РєРѕРЅСЃРѕР»СЊ `console.cloud.ru`; IaC вЂ” Terraform-РїСЂРѕРІР°Р№РґРµСЂ
  [`cloud-ru/evo-terraform`](https://github.com/cloud-ru/evo-terraform). Р”Р»СЏ РїРµСЂРµРЅРѕСЃР° СѓР¶Рµ
  СЃРѕР·РґР°РЅРЅРѕР№ Р’Рњ CLI РЅРµ РЅСѓР¶РµРЅ вЂ” СЂР°Р±РѕС‚Р°РµРј РїРѕ SSH РЅР°РїСЂСЏРјСѓСЋ.
- **Object Storage вЂ” S3-СЃРѕРІРјРµСЃС‚РёРјС‹Р№.** Р”Р»СЏ restic РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ С‚РѕС‚ Р¶Рµ `s3:`-backend,
  РјРµРЅСЏРµС‚СЃСЏ endpoint Рё СЃС‚Р°С‚РёС‡РµСЃРєРёРµ РєР»СЋС‡Рё (СЃРј. РЅРёР¶Рµ).
- **РџРѕСЂС‚ 25 РѕС‚РєСЂС‹С‚ РІ РѕР±Рµ СЃС‚РѕСЂРѕРЅС‹** (РІ РѕС‚Р»РёС‡РёРµ РѕС‚ Yandex Cloud, РіРґРµ 25/tcp Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅ).
  РџРѕСЌС‚РѕРјСѓ РїРѕС‡С‚Р° РјРѕР¶РµС‚ СЂР°Р±РѕС‚Р°С‚СЊ **РїРѕР»РЅРѕСЃС‚СЊСЋ СЃР°РјРѕСЃС‚РѕСЏС‚РµР»СЊРЅРѕ, Р±РµР· Postbox**: Stalwart
  РґРѕСЃС‚Р°РІР»СЏРµС‚ РїРѕ MX РїРѕР»СѓС‡Р°С‚РµР»СЏ РЅР°РїСЂСЏРјСѓСЋ. РўСЂРµР±СѓРµС‚СЃСЏ Р»РёС€СЊ РєРѕСЂСЂРµРєС‚РЅС‹Р№ PTR (РІ Evolution DNS
  РµСЃС‚СЊ PTR-Р·РѕРЅС‹) Рё Р·Р°РїРёСЃРё SPF/DKIM/DMARC/MX вЂ” Stalwart РіРµРЅРµСЂРёСЂСѓРµС‚ РіРѕС‚РѕРІС‹Р№ zone file СЃР°Рј.
  РС‚РѕРі РїСЂР°РєС‚РёРєРё вЂ” [`../docs/deployment/POSTMORTEM_CLOUDRU_MIGRATION.md`](../docs/deployment/POSTMORTEM_CLOUDRU_MIGRATION.md).
- **РћР±СЏР·Р°С‚РµР»СЊРЅРѕ: РјР°СЂС€СЂСѓС‚РёР·Р°С†РёСЏ РїСЂРё РґРІСѓС… РёРЅС‚РµСЂС„РµР№СЃР°С….** Р•СЃР»Рё Сѓ Р’Рњ РµСЃС‚СЊ Рё РІРЅСѓС‚СЂРµРЅРЅРёР№
  (`enp3s0`, 10.0.0.6), Рё direct-IP (`enp8s0`), DHCP РІС‹РґР°С‘С‚ **РґРІР° default-РјР°СЂС€СЂСѓС‚Р° СЃ
  РѕРґРёРЅР°РєРѕРІРѕР№ РјРµС‚СЂРёРєРѕР№** в†’ Р°СЃРёРјРјРµС‚СЂРёСЏ, СЃРѕРµРґРёРЅРµРЅРёСЏ СЂРІСѓС‚СЃСЏ (SSH/HTTP С‚Р°Р№РјР°СѓС‚СЏС‚, С…РѕС‚СЏ
  СЃРµСЂРІРёСЃС‹ СЃР»СѓС€Р°СЋС‚). Р¤РёРєСЃ вЂ” РїСЂРёРѕСЂРёС‚РµС‚РЅС‹Р№ default С‡РµСЂРµР· direct-IP:
  ```bash
  ip route replace default via <gw> dev enp8s0 metric 50
  ```
  РџСЂРѕРІРµСЂРєР°: `ip route get 8.8.8.8` РґРѕР»Р¶РµРЅ РїРѕРєР°Р·Р°С‚СЊ `dev enp8s0`. РЎРєСЂРёРїС‚ вЂ”
  [`cloudru-fix-routing.sh`](cloudru-fix-routing.sh) (СЃС‚Р°РІРёС‚СЃСЏ systemd-СЃРµСЂРІРёСЃРѕРј).

## РЁР°РіРё

### 0. РџСЂРµСЂРµРєРІРёР·РёС‚С‹ (РѕРїРµСЂР°С‚РѕСЂСЃРєР°СЏ Windows-СЃС‚Р°РЅС†РёСЏ)

- SSH-РєР»СЋС‡ Рє РЅРѕРІРѕР№ Р’Рњ (РїСѓС‚СЊ; РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ РІ СЃРєСЂРёРїС‚Р°С… вЂ” `~\.ssh\id_ed25519_yc_new`).
- TCP-РґРѕСЃС‚СѓРїРЅРѕСЃС‚СЊ `45.132.177.214` РЅР° 22/80/443 **РёР· Р Р¤** (РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Р№ gate, СѓСЂРѕРє 28.09):
  ```bash
  nc -vz 45.132.177.214 22
  curl -sS --connect-timeout 5 -o /dev/null -w '%{http_code}\n' http://45.132.177.214/
  ```
  Р•СЃР»Рё ICMP РїСЂРѕС…РѕРґРёС‚, Р° TCP вЂ” РЅРµС‚: СЃРјРµРЅРёС‚СЊ Р·Р°СЂРµР·РµСЂРІРёСЂРѕРІР°РЅРЅС‹Р№ Р°РґСЂРµСЃ, РЅРµ РїРµСЂРµРєР»СЋС‡Р°С‚СЊ DNS.

### 1. Security group (Cloud.ru console)

Р’ SG `Default` (РёР»Рё РѕС‚РґРµР»СЊРЅРѕР№) СЂР°Р·СЂРµС€РёС‚СЊ ingress:
`22/tcp`, `80/tcp`, `443/tcp`, `443/udp` (AmneziaWG), `465/587/143/993/4190/tcp`,
Рё РІРµСЃСЊ egress. РђРЅР°Р»РѕРі РїСЂР°РІРёР» РёР· `deploy.ps1` (СЃС‚Р°РґРёРё 3вЂ“4) Рё `cloud-init.yaml` (ufw).

Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕ РґР»СЏ Jami/JAMS (СЃРј. [`../docs/deployment/JAMS_SETUP.md`](../docs/deployment/JAMS_SETUP.md) В«РџРѕСЂС‚С‹В»):
`3478` tcp+udp, `5349` tcp+udp, СЂРµС‚СЂР°РЅСЃР»СЏС†РёСЏ `49160-49250/udp` (TURN),
`4222` tcp+udp (OpenDHT). `8081` (JAMS) Рё `8888` (DHT Proxy) РЅР°СЂСѓР¶Сѓ РќР• РѕС‚РєСЂС‹РІР°СЋС‚СЃСЏ вЂ” С‚РѕР»СЊРєРѕ С‡РµСЂРµР· Caddy.

### 2. РљРѕРґ РЅР° Р’Рњ

```bash
ssh -i <KEY> ubuntu@45.132.177.214
sudo mkdir -p /opt/msp/Newbie && sudo chown ubuntu:ubuntu /opt/msp/Newbie
git clone https://github.com/i1yxaluk-del/Newbie.git /opt/msp/Newbie
```

> Р‘Р°Р·РѕРІС‹Р№ РѕР±СЂР°Р· вЂ” Ubuntu 22.04 + Docker/Caddy/Node 20/unzip/restic. РќР° Cloud.ru
> `cloud-init.yaml` РёР· `deploy/yandex/` РІ РѕР±С‰РµРј РїСЂРёРјРµРЅРёРј, РЅРѕ `deploy.ps1` (yc) РЅРµ
> РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ вЂ” Cloud.ru Р’Рњ СЃРѕР·РґР°С‘С‚СЃСЏ РІ РєРѕРЅСЃРѕР»Рё. РњРёРЅРёРјР°Р»СЊРЅС‹Р№ РЅР°Р±РѕСЂ РїРѕСЃР»Рµ РѕР±СЂР°Р·Р°:
> `docker`, `docker compose` (plugin), `caddy`, `node 20` + `yarn` (corepack), `unzip`, `restic`, `ufw`.

### 3. Env-С„Р°Р№Р»С‹ (3 С€С‚., СЃРѕР·РґР°СЋС‚СЃСЏ Р·Р°РЅРѕРІРѕ вЂ” РЅРµ РєРѕРїРёСЂРѕРІР°С‚СЊ СЃС‚Р°СЂС‹Рµ cloud-РєСЂРµРґС‹)

`backend/.env`, `deploy/yandex/.env`, `deploy/yandex/monitoring/.env`.
РћР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ РєР»СЋС‡Рё вЂ” [`../docs/deployment/DEPLOY_RUNBOOK.md`](../docs/deployment/DEPLOY_RUNBOOK.md) В§3
Рё `preflight.sh`. РР· `backend.env.bak`/`deploy.env.bak` РїРµСЂРµРЅРѕСЃСЏС‚СЃСЏ С‚РѕР»СЊРєРѕ РґРѕРјРµРЅ,
Kaiten/Telegram/MAX-С‚РѕРєРµРЅС‹ Рё (РµСЃР»Рё Postbox РѕСЃС‚Р°С‘С‚СЃСЏ) Postbox-РєР»СЋС‡Рё.

### 4. Р“РµР№С‚ Рё СЃС‚РµРєРё

```bash
cd /opt/msp/Newbie && sudo bash scripts/deployment/preflight.sh --fix   # PRE-FLIGHT OK
cd deploy/yandex && docker compose up -d --build                         # mongo, backend, vaultwarden
cd monitoring && docker compose up -d --build                           # prometheus, grafana, am, max-alerter
```

### 5. Р’РѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёРµ РґР°РЅРЅС‹С…

```powershell
# РѕРїРµСЂР°С‚РѕСЂСЃРєР°СЏ Windows-СЃС‚Р°РЅС†РёСЏ (СЃРј. migration/migrate.ps1):
.\migration\migrate.ps1 -NewVmIp 45.132.177.214 -SshKeyPath <KEY>
```

`migrate.ps1` РєР»Р°РґС‘С‚ Р°СЂС‚РµС„Р°РєС‚С‹ РїР»РѕСЃРєРѕ РІ `/tmp/migration` Рё Р·Р°РїСѓСЃРєР°РµС‚ `restore-on-vm.sh`
(mongo `mongorestore --drop` в†’ С‚РѕРјР° в†’ max-session в†’ СЃС‚РµРєРё в†’ healthcheck).
РџРѕСЃР»Рµ вЂ” РїСЂРѕРІРµСЂРёС‚СЊ Stalwart РЅРµ РІ bootstrap: `docker logs msp-stalwart-1 | grep -c 'bootstrap mode'` в†’ `0`.

### 6. Caddy

`setup-on-vm.sh` СЃС‚Р°РІРёС‚ Р±РѕРµРІРѕР№ `Caddyfile` СЃ `MSP_DOMAIN`, Р»РёР±Рѕ РІСЂСѓС‡РЅСѓСЋ:
```bash
sudo install -m 0644 /opt/msp/Newbie/deploy/yandex/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/{$MSP_DOMAIN}/<DOMAIN>/g' /etc/caddy/Caddyfile
sudo mkdir -p /etc/systemd/system/caddy.service.d
printf '[Service]\nEnvironment="MSP_DOMAIN=<DOMAIN>"\n' | sudo tee /etc/systemd/system/caddy.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart caddy
```
РџСЂРѕРІРµСЂРєР°: `grep -c provisioning /etc/caddy/Caddyfile` в†’ `0`.

### 7. restic РЅР° Cloud.ru S3

РќРѕРІС‹Р№ СЂРµРїРѕР·РёС‚РѕСЂРёР№ (СЃС‚Р°СЂС‹Рµ YC S3-РєР»СЋС‡Рё РЅРµ РїРѕРґС…РѕРґСЏС‚ Рє РЅРѕРІРѕРјСѓ Р±Р°РєРµС‚Сѓ вЂ” `SignatureDoesNotMatch`):

```bash
# /etc/restic/env.sh
export AWS_ACCESS_KEY_ID=<Cloud.ru Key ID>
export AWS_SECRET_ACCESS_KEY=<Cloud.ru Key Secret>
export RESTIC_REPOSITORY=s3:https://<S3_ENDPOINT>/<bucket>
export RESTIC_PASSWORD=<РЅРѕРІС‹Р№/РїРµСЂРµРЅРµСЃС‘РЅРЅС‹Р№ РїР°СЂРѕР»СЊ>
```

> S3-СЌРЅРґРїРѕР№РЅС‚ Рё РёРјСЏ Р±Р°РєРµС‚Р° РІР·СЏС‚СЊ РёР· РєРѕРЅСЃРѕР»Рё Cloud.ru Object Storage (РїСЂРѕРІРµСЂРёС‚СЊ:
> `storage.cloud.ru` РґР»СЏ Evolution; С‚РѕС‡РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ РїРѕРєР°Р·Р°РЅРѕ РїСЂРё СЃРѕР·РґР°РЅРёРё Р±Р°РєРµС‚Р°/РєР»СЋС‡Р°).

```bash
restic init && sudo bash /opt/restic-scripts/backup.sh   # С‚РµСЃС‚РѕРІС‹Р№ СЃРЅР°РїС€РѕС‚
systemctl enable --now restic-backup.timer
```

### 8. AmneziaWG

РЎРµСЂРІРµСЂРЅС‹Рµ РєР»СЋС‡Рё СЃРѕС…СЂР°РЅРµРЅС‹ (`migration/awg-admin.conf`) вЂ” РѕР±РЅРѕРІРёС‚СЊ `Endpoint` РЅР° РЅРѕРІС‹Р№ IP
Рё СЂР°Р·РґР°С‚СЊ РєР»РёРµРЅС‚Р°Рј РѕР±РЅРѕРІР»С‘РЅРЅС‹Р№ С‚СѓРЅРЅРµР»СЊ. `net.ipv4.ip_forward=1`, MASQUERADE РЅР° eth0,
ufw `allow 443/udp` + SSH РёР· `10.9.0.0/24`.

### 9. Gates РґРѕ DNS switch (Рё РїРѕСЃР»Рµ)

- TCP-РґРѕСЃС‚СѓРїРЅРѕСЃС‚СЊ РЅРѕРІРѕРіРѕ IP РёР· Р Р¤ (22/80/443);
- `curl https://<domain>/api/health` в†’ ok (Р»РѕРєР°Р»СЊРЅРѕ, РґРѕ DNS);
- Mongo count Рё РІС‹Р±РѕСЂРѕС‡РЅС‹Рµ Р·Р°РїРёСЃРё; Vaultwarden login; Stalwart РЅРµ РІ bootstrap;
- MAX: `docker exec msp-max-alerter python -m max_alerter.auth` в†’ exit 0;
- С‚РµСЃС‚РѕРІС‹Р№ P1 в†’ MAX + email; РїРёСЃСЊРјРѕ РІРЅСѓС‚СЂСЊ/РЅР°СЂСѓР¶Сѓ;
- РЅРѕРІС‹Р№ restic snapshot; `du -sh` С‚РѕРјРѕРІ в‰€ Р±СЌРєР°Рї; РІРЅРµС€РЅРёР№ СЃРєР°РЅ РЅРµ РїРѕРєР°Р·С‹РІР°РµС‚ internal ports.

РЎС‚Р°СЂР°СЏ Р’Рњ вЂ” РІС‹РєР»СЋС‡РµРЅР° РґРѕ acceptance, СѓРґР°Р»СЏРµС‚СЃСЏ РїРѕСЃР»Рµ РїРѕРґС‚РІРµСЂР¶РґС‘РЅРЅРѕРіРѕ Р±СЌРєР°РїР° РЅРѕРІРѕР№ СЃСЂРµРґС‹.

### 10. Jami / JAMS-РёРЅС„СЂР°СЃС‚СЂСѓРєС‚СѓСЂР° (РїРёР»РѕС‚, 30.09.2026)

Р Р°Р·РІС‘СЂРЅСѓС‚Р° РЅР° С‚РѕР№ Р¶Рµ Р’Рњ РїРѕСЃР»Рµ РјРёРіСЂР°С†РёРё 28.09; РµС‘ РґР°РЅРЅС‹Рµ **РЅРµ РІС…РѕРґСЏС‚ РІ Р»РѕРєР°Р»СЊРЅС‹Р№ РєРёС‚
`migration/`** (С‚Р°Рј С‚РѕР»СЊРєРѕ pre-Jami Р°СЂС‚РµС„Р°РєС‚С‹). РСЃС‚РѕС‡РЅРёРє РґР°РЅРЅС‹С… вЂ” restic-СЃРЅР°РїС€РѕС‚С‹ СЃС‚Р°СЂРѕРіРѕ
YC-Р±Р°РєРµС‚Р° (`/opt`, `/etc`, `/home`) Р»РёР±Рѕ РїРµСЂРµСЃР±РѕСЂРєР° РїРѕ [`../docs/deployment/JAMS_SETUP.md`](../docs/deployment/JAMS_SETUP.md).

РљРѕРјРїРѕРЅРµРЅС‚С‹ Рё РёС… РґР°РЅРЅС‹Рµ:

| РљРѕРјРїРѕРЅРµРЅС‚ | Р Р°Р·РјРµС‰РµРЅРёРµ/РґР°РЅРЅС‹Рµ | РСЃС‚РѕС‡РЅРёРє РїСЂРё РїРµСЂРµРЅРѕСЃРµ |
|---|---|---|
| JAMS (8081, `m.`) | `/opt/jams/{CA.pem,keystore.jks,config.json,oauth.key,jams.crl}` + `jams.service` | restic `/opt/jams`, РёРЅР°С‡Рµ РїРµСЂРµСЃР±РѕСЂРєР° (JDK 26 + Maven + `git.jami.net/jami-jams`) |
| coturn (`turn.`, 3478/5349) | `/etc/turnserver.conf`, user `jami` | restic `/etc` + `turnadmin -a` |
| OpenDHT dhtnode (4222, `dht.`) | `dhtnode.service`, Р‘Р” dhtnode | РїРµСЂРµСЃР±РѕСЂРєР°: `apt install dhtnode` + unit (`tail -f /dev/null | dhtnode -v -p 4222 -b bootstrap.jami.net --proxyserver 8888`) |
| jami-services (compose `deploy/jami-services/`) | `/opt/jami-services/{pgdata,invite-data,ntfy-cache}` | restic `/opt/jami-services` + `pg_dump` nameservice (РІ `backup.sh`) |
| always-online jamid | `/home/jamiserver/.local/share/jami`, `jamiserver.service` | restic `/home` (РёРЅР°С‡Рµ headless D-Bus addAccount Р·Р°РЅРѕРІРѕ) |

- Р”РѕРї. DNS A-Р·Р°РїРёСЃРё (РІСЃРµ в†’ РЅРѕРІС‹Р№ IP): `m.`, `dht.`, `turn.`, `names.`, `invite.`, `push.`.
- Р”РѕРї. Caddy-Р±Р»РѕРєРё `m./dht./turn./names./invite./push.` (СЃС‚РёР»СЊ `{$MSP_DOMAIN}`) вЂ” `setup-on-vm.sh` РёС… РЅРµ СЃС‚Р°РІРёС‚, РґРѕР±Р°РІРёС‚СЊ РІ `/etc/caddy/Caddyfile` РІСЂСѓС‡РЅСѓСЋ.
- `jami-services` `.env`: `JAMI_PG_PASSWORD`, `JAMS_ADMIN_USER`, `JAMS_ADMIN_PASS`, `JAMS_ADMIN_PASSWORD` (Р·РЅР°С‡РµРЅРёСЏ вЂ” РёР· СЃРµРєСЂРµС‚РѕРІ/`~/msp-deploy-secrets.txt`, РєРѕС‚РѕСЂС‹С… РЅРµС‚ РІ Р»РѕРєР°Р»СЊРЅРѕРј РєРёС‚Рµ).
- РџР°СЂРѕР»Рё/CA JAMS Рё TURN вЂ” РІРѕСЃСЃС‚Р°РЅРѕРІРёС‚СЊ РёР· restic `/opt/jams`, `/etc/turnserver.conf`, `/home`; РїСЂРё РЅРµРґРѕСЃС‚СѓРїРЅРѕСЃС‚Рё restic вЂ” РїРµСЂРµСЃР±РѕСЂРєР° Рё РїРµСЂРµРІС‹РїСѓСЃРє (Р»РѕРіРёРЅС‹ JAMS РЅРµ РїРµСЂРµРёСЃРїРѕР»СЊР·СѓСЋС‚СЃСЏ РїРѕСЃР»Рµ revoke).

## РџРѕС‡С‚Р° Р±РµР· Postbox (РїСЂСЏРјР°СЏ РґРѕСЃС‚Р°РІРєР° РїРѕ MX)

Cloud.ru РЅРµ Р±Р»РѕРєРёСЂСѓРµС‚ 25/tcp, РїРѕСЌС‚РѕРјСѓ РІРЅРµС€РЅРёР№ СЂРµР»РµР№ РЅРµ РЅСѓР¶РµРЅ. РџРѕСЂСЏРґРѕРє:

1. **РЈР±РµРґРёС‚СЊСЃСЏ, С‡С‚Рѕ 25/tcp СЂР°Р·СЂРµС€С‘РЅ** РІ SG (ingress) Рё РІ ufw; РїСЂРѕРІРµСЂРёС‚СЊ РёСЃС…РѕРґСЏС‰РёР№:
   `python3 -c "import socket;socket.create_connection(('gmail-smtp-in.l.google.com',25),8)"`.
2. **РџРµСЂРµРєР»СЋС‡РёС‚СЊ Stalwart РЅР° РїСЂСЏРјСѓСЋ РґРѕСЃС‚Р°РІРєСѓ.** Р’ РµРіРѕ РєРѕРЅС„РёРіРµ (RocksDB, С‚РѕРј
   `stalwart-data`) РјР°СЂС€СЂСѓС‚ `mx` СѓР¶Рµ РµСЃС‚СЊ; СѓРґР°Р»РёС‚СЊ СЂРµР»РµР№ Postbox С‡РµСЂРµР· JMAP:
   ```bash
   PW=$(sudo grep '^STALWART_ADMIN_PASSWORD=' deploy/yandex/.env | cut -d= -f2-)
   # СЃРїРёСЃРѕРє: x:MtaRoute/get ; СѓРґР°Р»РёС‚СЊ СЂРµР»РµР№ (РёРјСЏ РѕР±С‹С‡РЅРѕ BaseYandex/postbox-outbound):
   curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
     -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/set",{"destroy":["<route-id>"]},"0"]]}' \
     http://127.0.0.1:8080/jmap/
   ```
   > env-РїРµСЂРµРјРµРЅРЅС‹Рµ Stalwart РїСЂРёРјРµРЅСЏСЋС‚СЃСЏ **С‚РѕР»СЊРєРѕ РїСЂРё РїРµСЂРІРѕРј Р·Р°РїСѓСЃРєРµ**; РїРѕСЃР»Рµ
   > РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ РєРѕРЅС„РёРіР° РёР· Р±СЌРєР°РїР° РїСЂР°РІРєРё вЂ” С‚РѕР»СЊРєРѕ С‡РµСЂРµР· JMAP/Admin UI.
3. **РћРїСѓР±Р»РёРєРѕРІР°С‚СЊ DNS-Р·Р°РїРёСЃРё.** Stalwart РіРµРЅРµСЂРёСЂСѓРµС‚ РїРѕР»РЅС‹Р№ zone file:
   `x:Domain/get` в†’ `dnsZoneFile` (СЃРѕС…СЂР°РЅС‘РЅ РІ [`../deploy/yandex/dns-zone-stalwart.txt`](../deploy/yandex/dns-zone-stalwart.txt)):
   DKIM (ed25519+rsa), `mail.` SPF (`v=spf1 a -all`), apex SPF (`v=spf1 mx -all`),
   MX в†’ `mail.<domain>`, DMARC (`p=reject`), SRV (imaps/submissions/jmap/caldav/carddav/pop3s),
   MTA-STS + TLS-RPT, CAA, autoconfig/autodiscover.
   > **Минимизация:** для почты реально нужны лишь 5 DNS-записей + PTR;
   > полный разбор и готовый набор — [../deploy/yandex/DNS_RECORDS.md](../deploy/yandex/DNS_RECORDS.md) и [../deploy/yandex/dns-zone-minimal.txt](../deploy/yandex/dns-zone-minimal.txt).
4. **PTR:** РІ РєРѕРЅСЃРѕР»Рё Cloud.ru в†’ **Evolution DNS в†’ РћР±СЂР°С‚РЅС‹Рµ Р·РѕРЅС‹** СЃРѕР·РґР°С‚СЊ PTR-Р·РѕРЅСѓ РґР»СЏ
   РїСѓР±Р»РёС‡РЅРѕРіРѕ IP в†’ `mail.<domain>` (РІР°Р¶РЅРѕ РґР»СЏ РґРѕСЃС‚Р°РІР»СЏРµРјРѕСЃС‚Рё; С‚РµРєСѓС‰РёР№ PTR РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ
   СЂР°РІРµРЅ РёРјРµРЅРё Р’Рњ).
5. **TLS РїРѕС‡С‚С‹:** РёРјРїРѕСЂС‚РёСЂРѕРІР°С‚СЊ Р°РєС‚СѓР°Р»СЊРЅС‹Р№ СЃРµСЂС‚РёС„РёРєР°С‚ Caddy РІ Stalwart Рё **РїРµСЂРµР·Р°РїСѓСЃС‚РёС‚СЊ**
   РєРѕРЅС‚РµР№РЅРµСЂ (Р±РµР· СЂРµСЃС‚Р°СЂС‚Р° listener РѕС‚РґР°С‘С‚ СЃС‚Р°СЂС‹Р№/self-signed):
   ```bash
   # x:Certificate/set СЃ certificate/privateKey РёР· /var/lib/caddy/.../mail.<domain>.{crt,key}
   sudo docker restart msp-stalwart-1
   echo | openssl s_client -connect 127.0.0.1:465 -servername mail.<domain> 2>/dev/null | openssl x509 -noout -dates
   ```
   РЎРєСЂРёРїС‚ вЂ” [`cloudru-mail-cert.sh`](cloudru-mail-cert.sh).
6. **РџСЂРѕРІРµСЂРєР°:** РїРёСЃСЊРјРѕ РЅР°СЂСѓР¶Сѓ (Gmail/РЇРЅРґРµРєСЃ) вЂ” РґРѕСЃС‚Р°РІР»РµРЅРѕ, DKIM `pass`; РїРёСЃСЊРјРѕ РІРЅСѓС‚СЂСЊ РЅР°
   `admin@<domain>` вЂ” РїРѕСЏРІРёР»РѕСЃСЊ РІ СЏС‰РёРєРµ; `openssl s_client` РѕС‚РґР°С‘С‚ LE-СЃРµСЂС‚РёС„РёРєР°С‚.

> РџРѕСЂС‚ 587/143 (STARTTLS) СЃРЅР°СЂСѓР¶Рё С„РёР»СЊС‚СЂСѓРµС‚СЃСЏ РѕР±Р»Р°РєРѕРј вЂ” РєР»РёРµРЅС‚Р°Рј СѓРєР°Р·С‹РІР°С‚СЊ implicit-TLS
> (`465` submission, `993` IMAP).

## РЎС‚Р°С‚СѓСЃ Рё С‡С‚Рѕ РѕСЃС‚Р°Р»РѕСЃСЊ

Р’С‹РїРѕР»РЅРµРЅРѕ:
- [x] pwsh РЅР° СЃС‚Р°РЅС†РёРё вЂ” РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅ РїРµСЂРµР·Р°РїСѓСЃРєРѕРј Harness (СЂР°Р±РѕС‚Р°РµРј РІ PowerShell 5.1).
- [x] SSH вЂ” `ubuntu@45.132.176.143`, РєР»СЋС‡ `~/.ssh/id_ed25519_yc_new`.
- [x] Р’Рњ/РґРёСЃРє/РёРЅС‚РµСЂС„РµР№СЃС‹/IP Рё РїРѕСЂС‚С‹ СЃРѕР·РґР°РЅС‹ С‡РµСЂРµР· API Cloud.ru Evolution.
- [x] РљРѕРґ, env, `preflight` в†’ OK; РґР°РЅРЅС‹Рµ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅС‹; СЃС‚РµРє healthy.
- [x] DNS A-Р·Р°РїРёСЃРё в†’ `45.132.176.143`; TLS РІС‹РїСѓС‰РµРЅ РґР»СЏ РІСЃРµС… РґРѕРјРµРЅРѕРІ.
- [x] РђСЃРёРјРјРµС‚СЂРёС‡РЅР°СЏ РјР°СЂС€СЂСѓС‚РёР·Р°С†РёСЏ РёСЃРїСЂР°РІР»РµРЅР° Рё Р·Р°РєСЂРµРїР»РµРЅР° systemd-СЃРµСЂРІРёСЃРѕРј.
- [x] РџРѕС‡С‚Р° РїРµСЂРµРІРµРґРµРЅР° РЅР° РїСЂСЏРјСѓСЋ РґРѕСЃС‚Р°РІРєСѓ Р±РµР· Postbox; TLS РїРѕС‡С‚С‹ РІР°Р»РёРґРµРЅ.

РћСЃС‚Р°Р»РѕСЃСЊ:
- [ ] **PTR** в†’ `mail.msp-claude.online` (Evolution DNS в†’ РћР±СЂР°С‚РЅС‹Рµ Р·РѕРЅС‹, РєРѕРЅСЃРѕР»СЊ).
- [ ] **РћРїСѓР±Р»РёРєРѕРІР°С‚СЊ DNS-Р·Р°РїРёСЃРё** РёР· [`../deploy/yandex/dns-zone-stalwart.txt`](../deploy/yandex/dns-zone-stalwart.txt) (SPF/DKIM/DMARC/MX/SRV/MTA-STS).
- [ ] **S3-СЃС‚Р°С‚РёС‡РµСЃРєРёРµ РєР»СЋС‡Рё** Object Storage + РёРјСЏ Р±Р°РєРµС‚Р° в†’ restic (`/etc/restic/env.sh`, `restic init`).
- [ ] AmneziaWG (`Endpoint` в†’ `45.132.176.143`), MAX re-auth, Jami/JAMS.
- [ ] РЎС‚Р°СЂС‹Р№ YC Object Storage вЂ” РЅСѓР¶РµРЅ Р»Рё (РёСЃС‚РѕСЂРёСЏ/Jami).
- [ ] РЈРґР°Р»РёС‚СЊ СЃС‚Р°СЂСѓСЋ Р’Рњ РїРѕСЃР»Рµ РїРµСЂРёРѕРґР° РЅР°Р±Р»СЋРґРµРЅРёСЏ.
