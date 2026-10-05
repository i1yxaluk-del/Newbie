#!/usr/bin/env bash
# Проверка, что нужные A-записи уже появились в DNS (иначе Caddy не выпустит сертификаты).
set -uo pipefail
echo "=== A-записи (спрашиваем 1.1.1.1, чтобы не ждать кэш) ==="
for h in x.msp-claude.online con.msp-claude.online e.msp-claude.online m.msp-claude.online; do
  ip=$(dig +short "$h" @1.1.1.1 2>/dev/null | grep -E '^[0-9]' | head -1)
  if [ "$ip" = "45.132.176.143" ]; then
    printf "  %-28s -> %s  ✅\n" "$h" "$ip"
  elif [ -z "$ip" ]; then
    printf "  %-28s -> НЕТ ЗАПИСИ ❌\n" "$h"
  else
    printf "  %-28s -> %s  ⚠️ (не наш IP)\n" "$h" "$ip"
  fi
done

echo
echo "=== текущие сертификаты Caddy ==="
sudo ls /var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/ 2>/dev/null | head -20 || \
  sudo find /var/lib/caddy -maxdepth 6 -name "*.crt" 2>/dev/null | sed 's#.*/##' | sort -u | head -20
echo DONE
