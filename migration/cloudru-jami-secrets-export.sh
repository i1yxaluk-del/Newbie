#!/usr/bin/env bash
# Формирует JSON-элементы Jami для импорта в Vaultwarden (значения не печатаются).
set -uo pipefail
sudo python3 - <<'PY'
import json, uuid, os, re

def parse(p):
    d = {}
    try:
        for line in open(p, encoding="utf-8", errors="replace"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"')
    except Exception:
        pass
    return d

JS = parse("/root/.jami-services.env") or parse("/opt/jami-services/.env")
TURN = parse("/root/.turn-pass")
SEC = parse("/root/.jami-secrets.txt")
JAMS_USER = SEC.get("JAMS_ADMIN_USER", JS.get("JAMS_ADMIN_USER", ""))
JAMS_PASS = SEC.get("JAMS_ADMIN_PASSWORD", JS.get("JAMS_ADMIN_PASSWORD", ""))

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

add("MSPShield · JAMS (админ Jami)", JAMS_USER, JAMS_PASS, "https://m.msp-claude.online",
    "Админ JAMS. Служба jams.service на ВМ (127.0.0.1:8081, наружу через Caddy m.msp-claude.online).\n"
    "ВАЖНО: порт 8081 захардкожен в launcher/AppStarter.java — при пересборке правку повторить.\n"
    "Артефакты CA (в бэкап!): /opt/jams/{CA.pem,keystore.jks,config.json,oauth.key,jams.crl}",
    [("ca_path", "/opt/jams/CA.pem"), ("admin_api", "https://m.msp-claude.online/api/login")])

add("MSPShield · coturn (TURN для Jami)", "jami", TURN.get("TURN_PASSWORD", ""),
    "turn:turn.msp-claude.online:3478",
    "coturn: TURN/STUN для Jami. Порты 3478 tcp/udp, 5349 tls, relay 49160-49250.\n"
    "realm=turn.msp-claude.online. Сертификат синхронизируется из Caddy (coturn-cert-sync.sh, cron 04:30).",
    [("tls_port", "5349"), ("config", "/etc/turnserver.conf")])

add("MSPShield · Jami-сервисы (names/invite/push)", "",
    JS.get("INVITE_ADMIN_TOKEN", ""),
    "https://invite.msp-claude.online/admin",
    "Стек /opt/jami-services (docker compose). Токены: INVITE_ADMIN_TOKEN — это поле пароля (админка приглашений).\n"
    "NAMES_ADMIN_TOKEN — API Name Service (https://names.msp-claude.online).\n"
    "JAMI_PG_PASSWORD — Postgres nameservice. Данные: /opt/jami-services/{pgdata,invite-data,ntfy-cache}.",
    [("names_admin_token", JS.get("NAMES_ADMIN_TOKEN", "")),
     ("pg_password", JS.get("JAMI_PG_PASSWORD", "")),
     ("ntfy", "https://push.msp-claude.online"),
     ("dht_proxy", "https://dht.msp-claude.online")])

out = {"encrypted": False, "folders": [], "items": items}
with open("/tmp/jami-items.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)

print(f"элементов Jami: {len(items)}")
for it in items:
    print(f"  • {it['name']:<45} логин={it['login']['username'] or '—':<12} пароль={'есть' if it['login']['password'] else 'НЕТ'}")
PY
sudo chmod 644 /tmp/jami-items.json
sudo ls -la /tmp/jami-items.json
echo DONE
