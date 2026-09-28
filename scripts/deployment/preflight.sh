#!/usr/bin/env bash
# Назначение: проверить repository и env перед production deploy без вывода секретов.
# Где запускать: на target VM из корня репозитория.
# Вход: backend/.env, deploy/yandex/.env, deploy/yandex/monitoring/.env.
# Побочные эффекты: с --fix нормализует CRLF/BOM и executable bit entrypoint.
# Проверка успеха: exit 0 и строка PRE-FLIGHT OK.
# Откат: при --fix исходные env сохраняются как *.preflight.bak.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FIX=false
[[ "${1:-}" == "--fix" ]] && FIX=true
FILES=("$ROOT/backend/.env" "$ROOT/deploy/yandex/.env" "$ROOT/deploy/yandex/monitoring/.env")

for file in "${FILES[@]}"; do
  [[ -f "$file" ]] || { echo "ERROR: нет $file" >&2; exit 1; }
  if head -c 3 "$file" | od -An -tx1 | grep -qi 'ef bb bf' || grep -q $'\r' "$file"; then
    if $FIX; then
      cp -a "$file" "$file.preflight.bak"
      python3 - "$file" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1]); raw = p.read_bytes()
if raw.startswith(b"\xef\xbb\xbf"): raw = raw[3:]
p.write_bytes(raw.replace(b"\r\n", b"\n"))
PY
      echo "FIXED: BOM/CRLF в $file"
    else
      echo "ERROR: BOM/CRLF в $file; повторите с --fix" >&2; exit 1
    fi
  fi
done

python3 - "${FILES[@]}" <<'PY'
from pathlib import Path
import sys
required = {
    "backend/.env": ["ADMIN_TOKEN", "MONGO_URL", "DB_NAME"],
    "deploy/yandex/.env": ["VAULTWARDEN_ADMIN_TOKEN"],
    "deploy/yandex/monitoring/.env": ["GRAFANA_ADMIN_PASSWORD", "ALERTMANAGER_WEBHOOK_TOKEN", "SMTP_AUTH_USER", "SMTP_AUTH_PASSWORD", "MAX_PHONE", "MAX_CHAT_ID"],
}
for filename in sys.argv[1:]:
    values = {}
    for line in Path(filename).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1); values[key.strip()] = value.strip()
    label = next(key for key in required if filename.endswith(key))
    missing = [key for key in required[label] if not values.get(key)]
    if missing: raise SystemExit(f"ERROR: {filename}: пустые {', '.join(missing)}")
print("ENV OK")
PY

ENTRY="$ROOT/deploy/yandex/monitoring/alertmanager/entrypoint.sh"
if [[ ! -x "$ENTRY" ]]; then
  $FIX && chmod +x "$ENTRY" || { echo "ERROR: $ENTRY не executable; повторите с --fix" >&2; exit 1; }
fi

# Контур сайта (урок миграции 28.09): заглушка cloud-init даёт 503,
# неразрешённый {$MSP_DOMAIN} не даёт Caddy стартовать. Проверяем оба состояния —
# жёстко на ВМ (если Caddyfile существует), мягко в CI (папки /etc/caddy нет).
[[ -f "$ROOT/deploy/yandex/Caddyfile" ]] || { echo "ERROR: нет deploy/yandex/Caddyfile" >&2; exit 1; }
if [[ -f /etc/caddy/Caddyfile ]]; then
  if grep -q 'provisioning in progress' /etc/caddy/Caddyfile; then
    echo "WARN: /etc/caddy/Caddyfile — заглушка cloud-init (сайт будет 503). Запустите setup-on-vm.sh (см. MIGRATION_RUNBOOK §9.3)." >&2
  fi
  if grep -q '{\$MSP_DOMAIN}' /etc/caddy/Caddyfile; then
    echo "WARN: в /etc/caddy/Caddyfile не подставлен MSP_DOMAIN — Caddy не стартует (см. setup-on-vm.sh)." >&2
  fi
fi
(cd "$ROOT/deploy/yandex" && docker compose config >/dev/null)
(cd "$ROOT/deploy/yandex/monitoring" && docker compose config >/dev/null)
grep -q 'secure_server:app' "$ROOT/deploy/yandex/Dockerfile.backend"
if grep -RqsE --include='*.sh' --include='*.ps1' --include='*.py' 'StrictHostKeyChecking=no' "$ROOT/migration"; then
  echo "ERROR: небезопасный SSH bypass (активное использование в скриптах)" >&2; exit 1
fi
echo "PRE-FLIGHT OK"
