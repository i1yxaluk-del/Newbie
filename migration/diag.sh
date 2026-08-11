#!/bin/bash
echo "=== PROMETHEUS TARGETS ==="
curl -s http://localhost:9090/api/v1/targets | python3 -c "
import sys, json
d = json.load(sys.stdin)
for t in d['data']['activeTargets']:
    job = t['labels'].get('job', '?')
    health = t['health']
    err = t.get('lastError', '')[:80]
    print(f'{job:25s} {health:8s} {err}')
"
echo ""
echo "=== RESTIC METRICS ==="
cat /var/lib/node_exporter/textfile_collector/restic_backup.prom 2>/dev/null || echo "NO METRICS FILE (restic not run yet)"
echo ""
echo "=== BLACKBOX CONFIG (targets) ==="
grep -A2 'targets:' /opt/msp/Newbie/deploy/yandex/monitoring/prometheus/blackbox.yml 2>/dev/null | head -20
