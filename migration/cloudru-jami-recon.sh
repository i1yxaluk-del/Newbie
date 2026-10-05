#!/usr/bin/env bash
# Проверка «пустых» секретов в backend/.env (без вывода значений) + сбор ключей Jami-стека.
set -uo pipefail
echo "=== backend/.env: какие переменные пусты ==="
sudo python3 - <<'PY'
import re
p = "/opt/msp/Newbie/backend/.env"
try:
    for line in open(p, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"')
        if re.search(r"(TOKEN|PASSWORD|SECRET|KEY)", k, re.I):
            print(f"  {k:<28} {'ЗАДАН (' + str(len(v)) + ' симв)' if v else 'ПУСТО'}")
except Exception as e:
    print("err", e)
PY
echo
echo "=== есть ли на ВМ следы Jami/JAMS (что осталось) ==="
for d in /opt/jams /opt/jams-src /opt/jami-services /etc/turnserver.conf /home/jamiserver /etc/systemd/system/jams.service /etc/systemd/system/jamiserver.service /etc/systemd/system/dhtnode.service; do
  if sudo test -e "$d"; then echo "  ЕСТЬ: $d"; else echo "  нет:  $d"; fi
done
echo
echo "=== restic/бэкап: настройки на ВМ ==="
sudo ls -la /etc/restic/ 2>/dev/null | head -5 || echo "  /etc/restic отсутствует"
sudo test -f /etc/restic/env.sh && echo "  /etc/restic/env.sh ЕСТЬ" || echo "  /etc/restic/env.sh нет"
echo
echo "=== в ките миграции (на ВМ) какие архивы ==="
sudo ls -la /opt/msp/Newbie/migration/ 2>/dev/null | grep -E '\.tar\.gz|\.archive' 
echo DONE
