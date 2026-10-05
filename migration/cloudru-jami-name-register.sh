#!/usr/bin/env bash
set -uo pipefail
echo "=== 1. как устроен jami-name-add ==="
cat /opt/jami-services/bin/jami-name-add 2>/dev/null

echo
echo "=== 2. текущие имена в nameservice ==="
TOK=$(grep '^NAMES_ADMIN_TOKEN=' /opt/jami-services/.env | cut -d= -f2-)
for ep in "/names" "/api/names" "/admin/names"; do
  printf "  %-14s -> " "$ep"
  curl -s -m 10 -H "X-Admin-Token: $TOK" "http://127.0.0.1:8889$ep" | head -c 250
  echo
done

echo
echo "=== 3. регистрирую ID узла как always-online ==="
/opt/jami-services/bin/jami-name-add "always-online" "c411a740567076504b776dc07b7b22d0d916034a" 2>&1 | head -c 300
echo

echo
echo "=== 4. проверка резолва через JAMS ==="
for id in c411a740567076504b776dc07b7b22d0d916034a db70df69875caa4a42cea0c7b6c051f639ede7a1; do
  printf "  %s… -> %s\n" "${id:0:14}" "$(curl -s -m 10 "http://127.0.0.1:8081/api/nameserver/addr/$id" | head -c 100)"
done
echo
echo "  обратный резолв по имени:"
curl -s -m 10 "http://127.0.0.1:8081/api/nameserver/name/always-online" | head -c 200; echo
echo DONE
