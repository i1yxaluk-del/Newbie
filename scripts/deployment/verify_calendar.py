#!/usr/bin/env python3
"""VM: проверить provisioned dashboard и метрики; credentials не печатаются."""
import base64
import json
import subprocess
from urllib.request import Request, urlopen
from urllib.parse import urlencode


def main():
    details = json.loads(subprocess.check_output(["docker", "inspect", "msp-grafana"]))[0]
    env = dict(item.split("=", 1) for item in details["Config"]["Env"] if "=" in item)
    auth = base64.b64encode((env.get("GF_SECURITY_ADMIN_USER", "admin") + ":" + env["GF_SECURITY_ADMIN_PASSWORD"]).encode()).decode()
    request = Request("http://127.0.0.1:3000/api/dashboards/uid/mspshield-backups", headers={"Authorization": "Basic " + auth})
    with urlopen(request, timeout=20) as response:
        dashboard = json.load(response)
    print("Grafana dashboard:", dashboard["dashboard"]["title"], dashboard["meta"]["url"])
    panel = next(p for p in dashboard["dashboard"]["panels"] if p.get("id") == 5)
    if panel["type"] != "table" or "msp_backup_day_status" not in panel["targets"][0]["expr"]:
        raise SystemExit("Calendar not provisioned in existing dashboard")
    print("Existing calendar panel:", panel["title"])
    for query in ["msp_backup_day_status", "time() - msp_backup_calendar_generated_seconds"]:
        with urlopen("http://127.0.0.1:9090/api/v1/query?" + urlencode({"query": query}), timeout=20) as response:
            data = json.load(response)
        results = data["data"]["result"]
        print(query, json.dumps([{"labels": item["metric"], "value": item["value"][1]} for item in results], ensure_ascii=True))
        if not results:
            raise SystemExit("Нет метрик календаря после scrape")


if __name__ == "__main__":
    main()
