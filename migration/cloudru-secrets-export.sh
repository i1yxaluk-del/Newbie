#!/usr/bin/env bash
# Собирает Bitwarden-JSON для импорта в Vaultwarden со свежими секретами прод-ВМ.
# Значения НЕ печатаются — только имена элементов и полей.
set -uo pipefail
sudo python3 - <<'PY'
import json, os, re, uuid, glob

def parse_env(path):
    d = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return d

def parse_secrets(path):
    d = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip().strip("[]")
                if "=" in line:
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip().strip('"')
                elif ":" in line and not line.startswith("#"):
                    k, v = line.split(":", 1)
                    d[k.strip()] = v.strip()
        # секции [NAME]
        cur = None
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^\s*\[(.+?)\]\s*$", line)
                if m:
                    cur = m.group(1).strip(); continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    key = f"{cur}.{k.strip()}" if cur else k.strip()
                    d[key] = v.strip().strip('"')
    except Exception:
        pass
    return d

DEPLOY = parse_env("/opt/msp/Newbie/deploy/yandex/.env")
BACK   = parse_env("/opt/msp/Newbie/backend/.env")
SEC    = parse_secrets("/home/ubuntu/msp-deploy-secrets.txt")
PM     = parse_secrets("/root/.postmaster-pass")

items = []
def add(name, user, pwd, uri="", notes="", fields=None):
    items.append({
        "id": str(uuid.uuid4()), "organizationId": None, "folderId": None,
        "type": 1, "reprompt": 0, "name": name, "notes": notes, "favorite": False,
        "fields": [{"name": n, "value": v, "type": 0} for n, v in (fields or [])],
        "login": {"username": user or "", "password": pwd or "", "totp": None,
                  "uris": [{"uri": uri}] if uri else []},
        "collectionIds": None,
    })

# 1. SSH на прод-ВМ
add("MSPShield · SSH прод-ВМ (Cloud.ru)", "ubuntu", "",
    "ssh://10.9.0.1",
    "Только через туннель AmneziaWG (awg-msp). Публичный IP 45.132.176.143, порт 22 закрыт снаружи (ufw + SG).\n"
    "Ключ: ~/.ssh/id_ed25519_yc_new (на операторской станции).\nАварийный доступ — веб-консоль Cloud.ru.",
    [("host_public", "45.132.176.143"), ("host_tunnel", "10.9.0.1"), ("ssh_key", "id_ed25519_yc_new")])

# 2. Stalwart (почта) — админка/JMAP
add("MSPShield · Stalwart Admin (почта)", "admin", DEPLOY.get("STALWART_ADMIN_PASSWORD", ""),
    "http://msp-cloud-vm:8080",
    "JMAP/админка Stalwart. Доступ только через туннель. Источник: deploy/yandex/.env (STALWART_ADMIN_PASSWORD).\n"
    "Почта: SMTP 465 / IMAP 993, сервер mail.msp-claude.online.",
    [("domain", "msp-claude.online")])

# 3. Grafana
add("MSPShield · Grafana", "admin", SEC.get("GRAFANA_ADMIN_PASSWORD", ""),
    "https://mon.msp-claude.online", "Логин admin. Источник: ~/msp-deploy-secrets.txt")

# 4. Vaultwarden admin
add("MSPShield · Vaultwarden Admin", "", SEC.get("VAULTWARDEN_ADMIN_TOKEN", DEPLOY.get("VAULTWARDEN_ADMIN_TOKEN", "")),
    "https://vault.msp-claude.online/admin",
    "Admin token (в поле password). Источник: ~/msp-deploy-secrets.txt")

# 5. Backend admin token
add("MSPShield · Backend ADMIN_TOKEN", "admin", BACK.get("ADMIN_TOKEN", ""),
    "https://msp-claude.online", "Токен админ-API лендинга/бэкенда. Источник: backend/.env")

# 6. Alertmanager webhook
add("MSPShield · Alertmanager webhook token", "", BACK.get("ALERTMANAGER_WEBHOOK_TOKEN", ""),
    "https://mon.msp-claude.online", "X-Webhook-Token для алертов. Источник: backend/.env")

# 7. Kaiten
add("MSPShield · Kaiten API", BACK.get("KAITEN_DOMAIN", ""), BACK.get("KAITEN_API_TOKEN", ""),
    f"https://{BACK.get('KAITEN_DOMAIN','')}" if BACK.get("KAITEN_DOMAIN") else "",
    "Токен Kaiten (лиды). Источник: backend/.env",
    [("space_id", BACK.get("KAITEN_SPACE_ID","")), ("board_id", BACK.get("KAITEN_BOARD_ID","")),
     ("column_id", BACK.get("KAITEN_COLUMN_ID",""))])

# 8. Telegram
add("MSPShield · Telegram bot (лиды)", "bot", BACK.get("TG_BOT_TOKEN", ""),
    "https://t.me", "Токен Telegram-бота. Источник: backend/.env",
    [("chat_id", BACK.get("TG_CHAT_ID","")), ("alert_chat_id", BACK.get("TG_ALERT_CHAT_ID",""))])

# 9. MAX
add("MSPShield · MAX бот (алерты)", BACK.get("MAX_BOT_USERNAME", ""), BACK.get("MAX_BOT_TOKEN", ""),
    "", "MAX-бот алертов. Источник: backend/.env",
    [("alert_chat_id", BACK.get("MAX_ALERT_CHAT_ID","")), ("webhook_secret", BACK.get("MAX_WEBHOOK_SECRET",""))])

# 10. MongoDB
add("MSPShield · MongoDB (прод)", "", BACK.get("MONGO_URL", ""),
    "mongodb://msp-mongo-1:27017", "Строка подключения с кредами (в поле password). Источник: backend/.env",
    [("db_name", BACK.get("DB_NAME",""))])

# 11. SMTP локальный (Stalwart)
add("MSPShield · SMTP локальный (postmaster@)", "postmaster@msp-claude.online", PM.get("POSTMASTER_PASSWORD",""),
    "smtps://mail.msp-claude.online:465",
    "Локальная почта Stalwart (прямая доставка, без Postbox). IMAP 993. Пароль также в /root/.postmaster-pass на ВМ.")

# 12. SMTP Postbox (legacy)
add("MSPShield · SMTP Postbox (legacy, выводим)", DEPLOY.get("SMTP_USERNAME", ""), DEPLOY.get("SMTP_PASSWORD", ""),
    "smtps://postbox.cloud.yandex.net:465", "Старый релей Yandex Postbox. Постепенно выводится из эксплуатации.")

# 13. Cloud.ru OAuth ключ
add("MSPShield · Cloud.ru API (OAuth ключ)", "1f661714363bcd70816b5bf2f4a4a66e", "",
    "https://console.cloud.ru", "OAuth-ключ Cloud.ru Evolution (keyId в логине). Секрет — в поле notes при необходимости.\n"
    "Проект e39dc535-25e8-4d64-9572-885b08a1f37e, зона ru.AZ-3. Токен: POST iam.api.cloud.ru/api/v1/auth/token")

folders = {}
out = {"encrypted": False, "folders": [], "items": items}
os.makedirs("/tmp", exist_ok=True)
with open("/tmp/vw-import.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)

print(f"элементов: {len(items)}")
for it in items:
    has_pwd = "пароль" if it["login"]["password"] else "—"
    print(f"  • {it['name']:<45} логин={it['login']['username'] or '—':<32} {has_pwd}")
PY
sudo chmod 644 /tmp/vw-import.json
sudo ls -la /tmp/vw-import.json
echo DONE
