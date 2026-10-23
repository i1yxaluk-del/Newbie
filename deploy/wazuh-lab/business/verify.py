#!/usr/bin/env python3
"""Проверить конкретный запуск: каждый case/правило, штатный SSH и панели.

Ищет только результаты настоящего manager. Не создаёт/исправляет документы индекса.
"""
import base64
import json
from pathlib import Path
import ssl
import time
from urllib.request import Request, urlopen

ROOT = Path("/home/service/wazuh-lab")


def main():
    credentials = json.loads((ROOT / "credentials.json").read_text())
    manifest = json.loads((ROOT / "business-last-run.json").read_text())
    headers = {"Authorization": "Basic " + base64.b64encode(("admin:" + credentials["admin"]).encode()).decode(),
               "Content-Type": "application/json"}
    context = ssl._create_unverified_context()

    def search(query):
        request = Request("https://127.0.0.1:9200/wazuh-alerts-*/_search",
                          data=json.dumps({"size": 100, "query": query, "sort": [{"timestamp": "desc"}]}).encode(), headers=headers)
        with urlopen(request, context=context, timeout=20) as response:
            return json.load(response)["hits"]["hits"]

    expected = {item["case"]: item["expected_rule"] for item in manifest["scenarios"]}
    results = {}
    native_rules = set()
    for attempt in range(24):
        hits = search({"term": {"data.msp.run_id": manifest["run_id"]}})
        results = {hit["_source"]["data"]["msp"]["case"]: str(hit["_source"]["rule"]["id"]) for hit in hits}
        native = search({"bool": {"filter": [{"term": {"location": "/var/ossec/lab/business-native.log"}}, {"term": {"data.dstuser": manifest["native_user"]}}]}})
        native_rules = {str(hit["_source"]["rule"]["id"]) for hit in native}
        if results == expected and set(manifest["native_expected_rules"]) <= native_rules:
            break
        time.sleep(5)
    report = {"run_id": manifest["run_id"], "custom_expected": expected, "custom_observed": results,
              "native_expected": manifest["native_expected_rules"], "native_observed": sorted(native_rules),
              "custom_pass": results == expected, "native_pass": set(manifest["native_expected_rules"]) <= native_rules}
    fim = search({"bool": {"filter": [{"term": {"syscheck.path": manifest["fim_path"]}},
                  {"range": {"timestamp": {"gte": manifest["generated_at"]}}}]}})
    report["fim_rules"] = sorted({str(hit["_source"]["rule"]["id"]) for hit in fim})
    report["fim_pass"] = bool({"550", "554"} & set(report["fim_rules"]))
    for identifier in ["overview", "continuity", "security"]:
        request = Request("https://192.168.114.10/api/saved_objects/dashboard/msp-business-" + identifier, headers=headers)
        with urlopen(request, context=context, timeout=20) as response:
            item = json.load(response)
        report["dashboard_" + identifier] = item["attributes"]["title"]
        # Проверить не только существование панели, но и ссылки/запрос каждой секции.
        for reference in item.get("references", []):
            ref_request = Request("https://192.168.114.10/api/saved_objects/" + reference["type"] + "/" + reference["id"], headers=headers)
            with urlopen(ref_request, context=context, timeout=20) as response:
                child = json.load(response)
            stored = json.loads(child["attributes"]["kibanaSavedObjectMeta"]["searchSourceJSON"])
            matches = search({"query_string": {"query": stored["query"]["query"]}})
            report.setdefault("panel_query_counts", {})[reference["id"]] = len(matches)
            if not matches:
                raise SystemExit("Запрос панели не возвращает события: " + reference["id"])
    (ROOT / "business-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["custom_pass"] or not report["native_pass"] or not report["fim_pass"]:
        raise SystemExit("Не все события подтверждены; см. конкретные expected/observed")


if __name__ == "__main__":
    main()
