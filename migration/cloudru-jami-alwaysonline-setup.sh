#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): поднимает always-online узел Jami (служба + D-Bus шина + техаккаунт).
# КОГДА ЗАПУСКАТЬ:         на ВМ от root при развёртывании Jami или если узел потерял аккаунт.
# КАК ЗАПУСКАТЬ:           sudo bash cloudru-jami-alwaysonline-setup.sh
# ПРОВЕРКА УСПЕХА:         systemctl is-active jamiserver -> active;
#                          journalctl -u jamiserver | grep 'Identity announcement succeeded'
# ОТКАТ:                   systemctl disable --now jamiserver; rm -rf /home/jamiserver/.local/share/jami
# ═══════════════════════════════════════════════════════════════════
# Исправление: jamid не запускался, т.к. скрипт писал лог в /var/log (нет прав у jamiserver).
# Теперь логи идут в journald, ожидание — по появлению имени в D-Bus, а не интроспекцией.
set -uo pipefail

cat >/usr/local/bin/jami-alwaysonline.sh <<'EOS'
#!/usr/bin/env bash
# Always-online узел Jami.
#   * поднимает сессионную D-Bus шину с ИЗВЕСТНЫМ адресом (/run/jami/bus.addr),
#     чтобы демоном можно было управлять снаружи;
#   * запускает jamid (ЛОГИ В JOURNALD — писать в /var/log у пользователя нет прав!);
#   * при первом старте создаёт техаккаунт (jami-ensure-account.sh).
set -uo pipefail
export HOME=/home/jamiserver
RUNDIR=/run/jami
mkdir -p "$RUNDIR"
chmod 700 "$RUNDIR"

eval "$(dbus-launch --sh-syntax)"
echo "$DBUS_SESSION_BUS_ADDRESS" > "$RUNDIR/bus.addr"
chmod 600 "$RUNDIR/bus.addr"
echo "шина: $DBUS_SESSION_BUS_ADDRESS"

/usr/libexec/jamid -p &
JAMID_PID=$!
echo "jamid pid=$JAMID_PID"

READY=0
for _ in $(seq 1 40); do
  if ! kill -0 "$JAMID_PID" 2>/dev/null; then
    echo "ОШИБКА: jamid завершился"
    wait "$JAMID_PID"
    exit 1
  fi
  if gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
       --method org.freedesktop.DBus.ListNames 2>/dev/null | grep -q "cx.ring.Ring"; then
    READY=1
    break
  fi
  sleep 2
done
echo "демон зарегистрирован в D-Bus: $READY"

if [ "$READY" = "1" ]; then
  /usr/local/bin/jami-ensure-account.sh || true
fi

wait "$JAMID_PID"
EOS
chmod 755 /usr/local/bin/jami-alwaysonline.sh

# в ensure-account убираем запись в /var/log
sed -i 's#>> /var/log/jami-account.log 2>&1##g' /usr/local/bin/jami-alwaysonline.sh 2>/dev/null || true

echo "=== перезапуск ==="
pkill -u jamiserver jamid 2>/dev/null || true
# убрать «осиротевшие» сессионные шины прошлых запусков
for p in $(pgrep -u jamiserver -x dbus-daemon); do kill "$p" 2>/dev/null || true; done
rm -f /var/log/jamid.log /var/log/jami-account.log 2>/dev/null || true
systemctl daemon-reload
systemctl restart jamiserver
sleep 50

echo -n "  служба: "; systemctl is-active jamiserver
echo "  процессы:"; pgrep -af "jamid|jami-alwaysonline" | head -4

echo
echo "=== журнал службы ==="
journalctl -u jamiserver -n 15 --no-pager 2>&1 | tail -15 | cut -c1-170

echo
echo "=== аккаунт уза через D-Bus ==="
BUS=$(cat /run/jami/bus.addr 2>/dev/null)
CM=cx.ring.Ring.ConfigurationManager
OBJ=/cx/ring/Ring/ConfigurationManager
LIST=$(sudo -u jamiserver env HOME=/home/jamiserver DBUS_SESSION_BUS_ADDRESS="$BUS" \
  gdbus call --session --dest cx.ring.Ring --object-path "$OBJ" --method $CM.getAccountList 2>&1)
echo "  getAccountList -> $LIST"
ACC=$(echo "$LIST" | grep -oE "[0-9a-f]{16}" | head -1)
if [ -n "$ACC" ]; then
  sudo -u jamiserver env HOME=/home/jamiserver DBUS_SESSION_BUS_ADDRESS="$BUS" \
    gdbus call --session --dest cx.ring.Ring --object-path "$OBJ" --method $CM.getAccountDetails "$ACC" > /tmp/ad2.txt 2>&1
  python3 - <<'PY'
import ast, re
raw = open("/tmp/ad2.txt", encoding="utf-8").read().strip()
try:
    d = ast.literal_eval(raw)[0]
    for k in ("Account.type","Account.username","Account.hostname","Account.alias","Account.enable","Account.status"):
        if k in d: print("  %s = %s" % (k, d[k]))
    print("  JAMI ID:", (re.findall(r"\b[0-9a-f]{40}\b", raw) or ["?"])[0])
except Exception as e:
    print("  (разбор не удался)", raw[:200])
PY
fi
echo DONE
