#!/usr/bin/env bash
# Проверка возможности самостоятельной отправки почты с ВМ cloud.ru (без Postbox).
echo "=== 1. Исходящий порт 25 (прямая доставка по MX) ==="
python3 - <<'PY'
import socket
targets = [("gmail-smtp-in.l.google.com",25), ("mx.yandex.net",25), ("mx.mail.ru",25)]
for host, port in targets:
    try:
        s = socket.create_connection((host, port), 8)
        banner = s.recv(160).decode(errors="replace").strip()
        print(f"  {host}:{port} -> OK: {banner!r}")
        s.close()
    except Exception as e:
        print(f"  {host}:{port} -> FAIL: {type(e).__name__}: {e}")
PY

echo "=== 2. Исходящие submission-порты (465/587 на внешние релеи) ==="
python3 - <<'PY'
import socket
targets = [("postbox.cloud.yandex.net",465), ("smtp.yandex.ru",465), ("smtp.mail.ru",465), ("smtp.gmail.com",587)]
for host, port in targets:
    try:
        s = socket.create_connection((host, port), 8)
        print(f"  {host}:{port} -> OK")
        s.close()
    except Exception as e:
        print(f"  {host}:{port} -> FAIL: {type(e).__name__}: {e}")
PY

echo "=== 3. PTR (reverse DNS) для публичного IP ==="
(host 45.132.176.143 2>/dev/null || getent hosts 45.132.176.143 || echo "  нет host/getent")
python3 - <<'PY'
import socket
try:
    print("  PTR:", socket.gethostbyaddr("45.132.176.143")[0])
except Exception as e:
    print("  PTR: нет ->", e)
PY

echo "=== 4. Текущая маршрутизация почты в Stalwart ==="
sudo docker inspect msp-stalwart-1 --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep -iE "ROUTE|POSTBOX|SMTP" | sed 's/\(SECRET\|PASSWORD\)=.*/\1=***/'
echo DONE
