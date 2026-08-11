#!/bin/bash
set -euo pipefail

docker exec msp-prometheus wget -qO /tmp/targets.json http://localhost:9090/api/v1/targets
docker exec msp-prometheus python3 - <<'PY'
import json

with open("/tmp/targets.json", encoding="utf-8") as source:
    targets = json.load(source)["data"]["activeTargets"]

for target in targets:
    labels = target["labels"]
    print(
        f'{labels.get("job", "unknown"):24} '
        f'{target["health"]:5} '
        f'{labels.get("instance", "")}'
    )
    if target.get("lastError"):
        print(f'  error: {target["lastError"]}')
PY
