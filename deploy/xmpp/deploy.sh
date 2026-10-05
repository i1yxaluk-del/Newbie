#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): разворачивает XMPP-сервер Prosody (актуальная версия).
# КОГДА ЗАПУСКАТЬ:         на ВМ от root, когда A-записи x. и con. указывают на наш IP.
# КАК ЗАПУСКАТЬ:           sudo bash deploy.sh
# ПРОВЕРКА УСПЕХА:         docker ps -> msp-prosody (healthy);
#                          в логе нет строк «Unable to load module»;
#                          5222 доступен снаружи, 5280 — только локально.
# ОТКАТ:                   cd /opt/xmpp && docker compose down
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail

SRC="/opt/msp/Newbie/deploy/xmpp"
DST="/opt/xmpp"
DOMAIN="x.msp-claude.online"
MUCDOMAIN="con.msp-claude.online"
CF=/etc/caddy/Caddyfile

echo "=== 1. файлы стека ==="
mkdir -p "$DST/certs"
for f in prosody.cfg.lua docker-compose.yml Dockerfile entrypoint.sh; do
  cp -f "$SRC/$f" "$DST/$f"
done
ls -la "$DST" | sed 's/^/  /'

echo
echo "=== 2. TURN-секрет ==="
if grep -q '^turn_external_secret = "__TURN_SECRET__"' "$DST/prosody.cfg.lua" 2>/dev/null; then
  TURN_SECRET=$(grep -E '^\s*static-auth-secret\s*=' /etc/turnserver.conf 2>/dev/null | head -1 | cut -d= -f2- | tr -d ' "'"'"'')
  if [ -z "$TURN_SECRET" ]; then
    TURN_SECRET=$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 32)
    cp /etc/turnserver.conf "/etc/turnserver.conf.bak.$(date +%s)"
    printf '\n# для XMPP/Matrix (XEP-0215: временные учётки TURN)\nuse-auth-secret\nstatic-auth-secret=%s\n' "$TURN_SECRET" >> /etc/turnserver.conf
    systemctl restart coturn; sleep 5
    echo -n "  coturn: "; systemctl is-active coturn
  fi
  sed -i "s|__TURN_SECRET__|$TURN_SECRET|" "$DST/prosody.cfg.lua"
else
  echo "  секрет уже подставлен при прошлом запуске"
fi

echo
echo "=== 3. блоки x. и con. в Caddyfile ==="
if ! grep -q "^x\.msp-claude\.online" "$CF"; then
  cp "$CF" "$CF.bak.$(date +%s)"
  cat >> "$CF" <<'EOS'

# x.* — XMPP (Prosody): HTTP-часть (upload/websocket) через 5280,
# сам XMPP клиенты открывают на порт 5222 напрямую.
x.msp-claude.online {
    encode gzip
    header -Server
    handle {
        reverse_proxy 127.0.0.1:5280
    }
}
EOS
  echo "  добавлен блок x."
fi
if ! grep -q "^con\.msp-claude\.online" "$CF"; then
  cat >> "$CF" <<'EOS'

# con.* — только ради сертификата для компонента конференций (трафик идёт внутри x.)
con.msp-claude.online {
    header -Server
    respond "MSPShield XMPP conference" 200
}
EOS
  echo "  добавлен блок con."
fi
if caddy validate --config "$CF" 2>&1 | grep -qi error; then
  caddy validate --config "$CF" 2>&1 | tail -3
  cp "$(ls -1t "$CF".bak.* | head -1)" "$CF"
  echo "  ОШИБКА конфига Caddy — откатил"; exit 1
fi
systemctl reload caddy && echo "  caddy перезагружен"

echo
echo "=== 4. ожидание сертификатов от Caddy ==="
CERTBASE="/var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory"
for d in "$DOMAIN" "$MUCDOMAIN"; do
  for i in $(seq 1 24); do
    [ -f "$CERTBASE/$d/$d.crt" ] && break
    sleep 5
  done
  if [ -f "$CERTBASE/$d/$d.crt" ]; then
    cp "$CERTBASE/$d/$d.crt" "$DST/certs/$d.crt"
    cp "$CERTBASE/$d/$d.key" "$DST/certs/$d.key"
    chmod 644 "$DST/certs/$d.crt"; chmod 640 "$DST/certs/$d.key"
    echo "  $d: сертификат на месте"
  else
    echo "  $d: ⚠️ сертификат ещё не выпущен"
  fi
done
chmod 755 "$DST/certs"

echo
echo "=== 5. сборка и запуск ==="
cd "$DST"
docker compose down --remove-orphans 2>&1 | tail -2
docker compose build 2>&1 | tail -5
docker compose up -d 2>&1 | tail -3
sleep 25
docker compose ps

echo
echo "=== 6. проверка модулей (не должно быть «Unable to load») ==="
docker logs msp-prosody 2>&1 | grep -iE "unable to load|error" | head -8 | sed 's/^/  /' || echo "  ошибок загрузки модулей нет ✅"

echo
echo "=== 7. админская учётка ==="
if docker exec -u prosody msp-prosody prosodyctl user list "$DOMAIN" 2>/dev/null | grep -q "admin@"; then
  echo "  admin@$DOMAIN уже существует"
else
  ADMIN_PASS=$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 20)
  docker exec -u prosody msp-prosody prosodyctl register admin "$DOMAIN" "$ADMIN_PASS" 2>&1 | tail -2
  echo "admin@$DOMAIN / $ADMIN_PASS" >> /root/.xmpp-admin.txt
  chmod 600 /root/.xmpp-admin.txt
  echo "  создано, пароль в /root/.xmpp-admin.txt"
fi

echo
echo "=== 8. порты и доступность ==="
ss -lntp 2>/dev/null | grep -E ":5222|:5280" | sed 's/^/  /'
echo -n "  5222 снаружи: "
timeout 8 bash -c "cat < /dev/null > /dev/tcp/45.132.176.143/5222" 2>/dev/null && echo да || echo "НЕТ (проверить SG)"
echo -n "  https://$DOMAIN (upload): "
curl -s -o /dev/null -w '%{http_code}\n' -m 10 "https://$DOMAIN/" || echo "нет ответа"
echo
echo "=== 9. версия и состояние ==="
docker exec -u prosody msp-prosody prosodyctl about 2>&1 | head -3 | sed 's/^/  /'
echo XMPP_DEPLOY_DONE
