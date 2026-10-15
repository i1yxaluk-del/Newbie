#!/usr/bin/env python3
"""VM: integrate calendar panel into existing dashboard, preserving other panels.
Input: uploaded reference mspshield-backups.json. Backup before replacing live JSON.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

directory = Path("/opt/msp/Newbie/deploy/yandex/monitoring/grafana/dashboards")
target = directory / "mspshield-backups.json"
reference = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
current = json.loads(target.read_text(encoding="utf-8-sig"))
if current.get("uid") != "mspshield-backups":
    raise SystemExit("Unexpected dashboard UID")
panel = next(p for p in reference["panels"] if p.get("title") == "Календарь backup · 7 дней МСК")
history = next(p for p in current["panels"] if p.get("id") == 5)
panel["gridPos"] = history["gridPos"]
panel["id"] = history["id"]
backup = Path("/var/backups/mspshield-grafana") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup.mkdir(parents=True, exist_ok=False)
shutil.copy2(target, backup / target.name)
current["panels"] = [panel if p.get("id") == history["id"] else p for p in current["panels"]]
current["version"] = int(current.get("version", 0)) + 1
temporary = target.with_suffix(".tmp")
temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
temporary.chmod(0o644)
temporary.replace(target)
standalone = directory / "msp-backup-calendar.json"
if standalone.exists():
    shutil.move(str(standalone), backup / standalone.name)
print("Integrated existing dashboard /d/mspshield-backups; backup:", backup)
