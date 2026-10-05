#!/usr/bin/env bash
set -uo pipefail
PM=$(sudo cat /root/.postmaster-pass | cut -d= -f2-)
python3 - "$PM" <<'PY'
import smtplib, ssl, sys
pw = sys.argv[1]
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
from email.message import EmailMessage
m = EmailMessage()
m["From"] = "postmaster@msp-claude.online"
m["To"] = "maksivanovz@yandex.ru"
m["Subject"] = "MSPShield: тест почты после миграции на Cloud.ru"
m.set_content(
    "Проверка почты MSPShield после миграции с Yandex Cloud на Cloud.ru.\n"
    "Отправитель: postmaster@msp-claude.online (прямая доставка, без Postbox).\n\n"
    "Пожалуйста, откройте письмо -> «Показать оригинал» и проверьте заголовки:\n"
    "  Received-SPF: pass\n  dkim=pass (должно быть дважды: rsa и ed25519)\n  dmarc=pass\n"
)
with smtplib.SMTP_SSL("127.0.0.1", 465, context=ctx, timeout=30) as s:
    s.login("postmaster@msp-claude.online", pw)
    s.send_message(m)
print("SENT OK -> maksivanovz@yandex.ru")
PY
echo "=== ждём доставку (30 c) ==="
sleep 30
echo "=== логи: доставка на yandex ==="
sudo docker exec msp-stalwart-1 sh -c 'tail -n 200 /var/lib/stalwart/logs/* 2>/dev/null' \
  | grep -iE "yandex\.ru|delivery\.|dkim|signature|starttls|remote server|queue\.rescheduled|completed" \
  | tail -25
echo "=== ошибки/предупреждения ==="
sudo docker exec msp-stalwart-1 sh -c 'tail -n 200 /var/lib/stalwart/logs/* 2>/dev/null' \
  | grep -iE "error|fail|reject|bounce" | tail -10
echo DONE
