#!/usr/bin/env bash
# no-cache для HTML/SPA-маршрутов JAMS: иначе браузер держит старый index.html
# и после обновления грузит прежний бандл (мы на это уже натыкались).
set -uo pipefail
CF=/etc/caddy/Caddyfile
cp "$CF" "$CF.bak.$(date +%s)"

python3 - <<'PY'
p = "/etc/caddy/Caddyfile"
s = open(p, encoding="utf-8").read()
anchor = """    handle @spa {
        rewrite * /index.html
        reverse_proxy 127.0.0.1:8081
    }"""
if "Cache-Control" in s and "no-cache" in s:
    print("уже добавлено")
elif anchor in s:
    s = s.replace(anchor, """    # HTML не кэшируем: после обновления JAMS браузер должен взять новый бандл.
    header @spa Cache-Control "no-cache, must-revalidate"

""" + anchor)
    open(p, "w", encoding="utf-8").write(s)
    print("добавлен no-cache для SPA-маршрутов")
else:
    print("ЯКОРЬ НЕ НАЙДЕН — правка не применена")
PY

echo "=== validate + reload ==="
if caddy validate --config "$CF" 2>&1 | grep -qi error; then
  caddy validate --config "$CF" 2>&1 | tail -4
  LAST=$(ls -1t "$CF".bak.* | head -1); cp "$LAST" "$CF"; echo "откат"
else
  echo "конфиг валиден"; systemctl reload caddy && echo "reload OK"
fi
sleep 5
echo -n "caddy: "; systemctl is-active caddy
echo
echo "=== проверка заголовков ==="
echo "--- /signin ---"
curl -s -D - -o /dev/null -m 12 --resolve m.msp-claude.online:443:127.0.0.1 "https://m.msp-claude.online/signin" | grep -iE "^HTTP|cache-control|content-type"
echo "--- / (корень) ---"
curl -s -D - -o /dev/null -m 12 --resolve m.msp-claude.online:443:127.0.0.1 "https://m.msp-claude.online/" | grep -iE "^HTTP|cache-control"
echo "--- бандл (должен кэшироваться) ---"
JS=$(curl -s -m 10 http://127.0.0.1:8081/ | grep -oE 'static/js/main\.[a-z0-9]+\.js' | head -1)
curl -s -D - -o /dev/null -m 15 --resolve m.msp-claude.online:443:127.0.0.1 "https://m.msp-claude.online/$JS" | grep -iE "^HTTP|cache-control"
echo DONE
