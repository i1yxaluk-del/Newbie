#!/usr/bin/env bash
# SPA-fallback для m.msp-claude.online: /signin и прочие пути React Router
# должны отдавать index.html, а не 404 от Tomcat.
set -uo pipefail
CF=/etc/caddy/Caddyfile
cp "$CF" "$CF.bak.$(date +%s)"

echo "=== 0. отдаёт ли JAMS /index.html ==="
curl -s -o /dev/null -w '  /index.html -> %{http_code}\n' -m 8 http://127.0.0.1:8081/index.html

echo "=== 1. заменяю блок m.msp-claude.online ==="
python3 - <<'PY'
p = "/etc/caddy/Caddyfile"
s = open(p, encoding="utf-8").read()
key = "m.msp-claude.online {"
if key not in s:
    raise SystemExit("блок m.msp-claude.online не найден")
start = s.index(key)
i = s.index("{", start)
depth = 0
end = None
for j in range(i, len(s)):
    if s[j] == "{":
        depth += 1
    elif s[j] == "}":
        depth -= 1
        if depth == 0:
            end = j + 1
            break
new = """m.msp-claude.online {
    encode gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        -Server
    }

    # API JAMS — проксируем как есть.
    handle /api/* {
        reverse_proxy 127.0.0.1:8081
    }

    # SPA (React Router): путь без расширения -> index.html.
    # Без этого прямой переход/перезагрузка на /signin отдаёт 404 от Tomcat.
    @spa {
        not path /api/*
        not path *.js *.css *.map *.png *.jpg *.jpeg *.gif *.svg *.ico *.json *.txt *.woff *.woff2 *.ttf *.eot
    }
    handle @spa {
        rewrite * /index.html
        reverse_proxy 127.0.0.1:8081
    }

    handle {
        reverse_proxy 127.0.0.1:8081
    }
}"""
s = s[:start] + new + s[end:]
open(p, "w", encoding="utf-8").write(s)
print("блок заменён")
PY

echo "=== 2. validate + reload ==="
if caddy validate --config "$CF" 2>&1 | grep -qi error; then
  caddy validate --config "$CF" 2>&1 | tail -4
  echo "ОШИБКА — откат"
  LAST=$(ls -1t "$CF".bak.* | head -1); cp "$LAST" "$CF"
else
  echo "конфиг валиден"
  systemctl reload caddy && echo "reload OK"
fi
sleep 5
systemctl is-active caddy

echo "=== 3. проверка ==="
for p in "/" "/signin" "/signup" "/api/info"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 --resolve m.msp-claude.online:443:127.0.0.1 "https://m.msp-claude.online$p")
  echo "  $p -> $code"
done
echo DONE
