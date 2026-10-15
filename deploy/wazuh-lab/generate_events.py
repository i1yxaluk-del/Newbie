#!/usr/bin/env python3
"""Безопасные учебные события: только JSONL и файл в выделенном каталоге lab.
Не выполняет атаки, сканирование, блокировки или изменения системных настроек.
VM: sudo python3 generate_events.py --root /home/service/wazuh-lab/training
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", default="/home/service/wazuh-lab/training")
args = parser.parse_args()
root = Path(args.root)
if not (root / "events.jsonl").is_file() or not (root / "fim").is_dir():
    raise SystemExit("Сначала подготовьте изолированный lab")
run = str(uuid.uuid4())
with (root / "events.jsonl").open("a", encoding="utf-8") as output:
    for scenario in ["baseline", "backup_failed", "access_review", "policy_drift"]:
        output.write(json.dumps({"lab": "msp-junior", "synthetic": True, "scenario": scenario, "run_id": run, "timestamp": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False) + "\n")
(root / "fim" / "training-policy.txt").write_text("Synthetic FIM exercise " + run + "\n", encoding="utf-8")
print("Synthetic events appended; run_id=" + run)
