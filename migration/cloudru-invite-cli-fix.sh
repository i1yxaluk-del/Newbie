#!/usr/bin/env bash
set -uo pipefail
echo "=== 1. что лежит в /opt/jami-services/bin ==="
ls -la /opt/jami-services/bin/ 2>&1
echo
echo "=== 2. что есть в репозитории ==="
ls -la /opt/msp/Newbie/deploy/jami-services/bin/ 2>&1
echo
echo "=== 3. права в репозитории (git) ==="
cd /opt/msp/Newbie && git ls-files -s deploy/jami-services/bin/
echo
echo "=== 4. делаю CLI исполняемыми и кладу на место ==="
for f in jami-name-add jami-invite-create; do
  if [ -f "/opt/msp/Newbie/deploy/jami-services/bin/$f" ]; then
    cp "/opt/msp/Newbie/deploy/jami-services/bin/$f" "/opt/jami-services/bin/$f"
    chmod 755 "/opt/jami-services/bin/$f"
    echo "  установлен: $f"
  else
    echo "  НЕТ в репозитории: $f"
  fi
done
ls -la /opt/jami-services/bin/ 2>&1
echo
echo "=== 5. как CLI берёт токен/URL ==="
head -25 /opt/jami-services/bin/jami-invite-create 2>/dev/null
echo DONE
