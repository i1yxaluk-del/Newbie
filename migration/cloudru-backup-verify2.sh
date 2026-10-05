#!/usr/bin/env bash
set -uo pipefail
echo "=== 1. метрика бэкапа в Prometheus ==="
curl -s -m 15 "http://127.0.0.1:9090/api/v1/query?query=restic_backup_success" > /tmp/q1.json 2>/dev/null
python3 - <<'PY'
import json
try:
    d = json.load(open("/tmp/q1.json"))
    res = d.get("data", {}).get("result", [])
    if not res:
        print("  пусто — Prometheus ещё не собрал метрику (подожди 30 c) или target не scrape-ится")
    for r in res:
        m = r.get("metric", {})
        print("  restic_backup_success host=%s repo=%s => %s" % (m.get("host"), m.get("repo"), r.get("value", ["", "?"])[1]))
except Exception as e:
    print("  err:", e)
PY

echo
echo "=== 2. таргеты Prometheus ==="
curl -s -m 15 "http://127.0.0.1:9090/api/v1/targets" > /tmp/t.json 2>/dev/null
python3 - <<'PY'
import json
try:
    d = json.load(open("/tmp/t.json"))
    for t in d["data"]["activeTargets"]:
        job = t["labels"].get("job", "")
        if any(k in job for k in ("node", "mon", "backup")) or "9100" in t.get("scrapeUrl", ""):
            print("  %-18s %-45s %s" % (job, t.get("scrapeUrl"), t.get("health")))
except Exception as e:
    print("  err:", e)
PY

echo
echo "=== 3. правила бэкапов в Prometheus ==="
curl -s -m 15 "http://127.0.0.1:9090/api/v1/rules" > /tmp/r.json 2>/dev/null
python3 - <<'PY'
import json
try:
    d = json.load(open("/tmp/r.json"))
    for g in d["data"]["groups"]:
        if "backup" in g["name"].lower():
            names = ", ".join(r["name"] for r in g["rules"])
            print("  группа %s: %s" % (g["name"], names))
    else:
        print("  (группы: %s)" % ", ".join(g["name"] for g in d["data"]["groups"]))
except Exception as e:
    print("  err:", e)
PY

echo
echo "=== 4. node-exporter: видит ли файл (изнутри контейнера) ==="
sudo docker exec msp-node-exporter sh -c 'ls /var/lib/node_exporter/textfile_collector/ 2>/dev/null; wget -qO- http://127.0.0.1:9100/metrics 2>/dev/null | grep -c "^restic_" || echo "wget нет"' 2>/dev/null
echo
echo "=== 5. Grafana: дашборд и папка ==="
ls -la /var/lib/grafana/dashboards 2>/dev/null | head -5 || \
sudo docker exec msp-grafana sh -c 'ls -la /var/lib/grafana/dashboards | head -8' 2>/dev/null
echo DONE
