#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): Добавляет в Caddyfile блоки Jami-хостов (m./dht./turn./names./invite./push.).
# КОГДА ЗАПУСКАТЬ:         На ВМ от root при развёртывании Jami.
# КАК ЗАПУСКАТЬ:           sudo bash cloudru-caddy-jami2.sh
# ПРОВЕРКА УСПЕХА:         caddy validate -> валиден; 6 сертификатов в хранилище Caddy.
# ОТКАТ:                   Восстановить /etc/caddy/Caddyfile из .bak.* и перезагрузить caddy.
# ═══════════════════════════════════════════════════════════════════
# Исправленные блоки Jami: header-директивы — валидный синтаксис.
set -uo pipefail
CF=/etc/caddy/Caddyfile

echo "=== откат к последнему бэкапу (убрать битые блоки) ==="
LAST=$(ls -1t "$CF".bak.* 2>/dev/null | head -1)
if [ -n "$LAST" ]; then cp "$LAST" "$CF"; echo "восстановлен из $LAST"; else echo "бэкап не найден"; fi
grep -c 'msp-claude.online' "$CF" | sed 's/^/строк с доменом: /'

echo "=== добавляю корректные блоки ==="
cat >>"$CF" <<'EOF'

# ─── Jami / JAMS (self-hosted: JAMS + coturn + OpenDHT + сервисы) ───
# JAMS Web UI (Java-сервер, 127.0.0.1:8081)
m.msp-claude.online {
    encode gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        -Server
    }
    handle {
        reverse_proxy 127.0.0.1:8081
    }
}

# DHT Proxy REST (dhtnode, 127.0.0.1:8888) — для мобильных клиентов Jami
dht.msp-claude.online {
    encode gzip
    header -Server
    handle {
        reverse_proxy 127.0.0.1:8888
    }
}

# turn.* — веб-морды нет; блок нужен только чтобы Caddy выпустил
# сертификат, который затем читает coturn (coturn-cert-sync.sh)
turn.msp-claude.online {
    header -Server
    respond "MSP Cloud TURN — certificate holder" 404
}

# Name Service (FastAPI, 127.0.0.1:8889)
names.msp-claude.online {
    encode gzip
    header -Server
    handle {
        reverse_proxy 127.0.0.1:8889
    }
}

# Портал приглашений (FastAPI, 127.0.0.1:8890)
invite.msp-claude.online {
    encode gzip
    header -Server
    handle {
        reverse_proxy 127.0.0.1:8890
    }
}

# UnifiedPush / ntfy (127.0.0.1:8891) — без gzip
push.msp-claude.online {
    header -Server
    handle {
        reverse_proxy 127.0.0.1:8891
    }
}
EOF

echo "=== validate ==="
if caddy validate --config "$CF" 2>&1 | grep -qi error; then
  caddy validate --config "$CF" 2>&1 | tail -5
  echo "ОШИБКА ВАЛИДАЦИИ — откатываю"
  cp "$LAST" "$CF"; caddy validate --config "$CF" 2>&1 | tail -2
else
  echo "конфиг валиден"
  systemctl reload caddy && echo "reload OK"
fi
sleep 8
systemctl is-active caddy
echo "=== ожидаю выпуск сертификатов (до 60с) ==="
for i in 1 2 3 4 5 6; do
  sleep 10
  N=$(sudo ls -1 /var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/ 2>/dev/null | wc -l)
  echo "  попытка $i: сертификатов $N"
  [ "$N" -ge 10 ] && break
done
sudo ls -1 /var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/ 2>/dev/null
echo DONE
