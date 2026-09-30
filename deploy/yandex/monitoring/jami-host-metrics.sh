#!/bin/bash
# Jami host-метрики для node_exporter (textfile collector).
# Запуск: cron каждую минуту от root.
OUT=/var/lib/node_exporter/textfile_collector/jami.prom
TMP="${OUT}.tmp"

TURN=$(ss -H -a -n 2>/dev/null | grep -E ':(3478|5349)\b' | grep -c ESTAB)
DHT=$(ss -H -t -n state established "( sport = :8888 )" 2>/dev/null | wc -l | tr -d ' ')
if systemctl is-active --quiet jamiserver; then DAEMON=1; else DAEMON=0; fi

cat > "$TMP" <<EOF
# HELP jami_turn_sessions Established client sessions on TURN ports (3478/5349)
# TYPE jami_turn_sessions gauge
jami_turn_sessions $TURN
# HELP jami_dht_proxy_clients Established TCP clients on DHT proxy :8888
# TYPE jami_dht_proxy_clients gauge
jami_dht_proxy_clients $DHT
# HELP jami_daemon_up jamiserver (always-online jamid) active, 1/0
# TYPE jami_daemon_up gauge
jami_daemon_up $DAEMON
EOF
mv "$TMP" "$OUT"
chmod 644 "$OUT"
