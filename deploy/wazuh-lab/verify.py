#!/usr/bin/env python3
"""Проверка lab: credentials только в памяти, stdout — статусы и число событий."""
import base64
import json
from pathlib import Path
import ssl
import subprocess
import time
from urllib.request import Request, urlopen

root = Path("/home/service/wazuh-lab")
credentials = json.loads((root / "credentials.json").read_text())
# Локальный self-signed TLS: этот verifier применяется только к loopback lab indexer.
context = ssl._create_unverified_context()
auth = base64.b64encode(("admin:" + credentials["admin"]).encode()).decode()


def request(path, body=None, method=None):
    req = Request("https://127.0.0.1:9200" + path, data=json.dumps(body).encode() if body is not None else None,
                  headers={"Authorization": "Basic " + auth, "Content-Type": "application/json"}, method=method)
    with urlopen(req, context=context, timeout=20) as response:
        return json.load(response)


for attempt in range(24):
    try:
        health = request("/_cluster/health")
        print("Indexer cluster:", health["status"])
        break
    except Exception as exc:
        if attempt == 23:
            raise SystemExit("Indexer not ready: " + type(exc).__name__)
        time.sleep(5)
query = {"query": {"term": {"rule.groups": "msp_lab"}}}
try:
    results = request("/wazuh-alerts-*/_count", query)
    print("Indexed synthetic training alerts:", results.get("count"))
except Exception as exc:
    print("Training index query:", type(exc).__name__)
status = subprocess.run(["curl", "-k", "-s", "-o", "/dev/null", "-w", "%{http_code}", "https://192.168.114.10"], capture_output=True, text=True)
print("Dashboard HTTP:", status.stdout)
