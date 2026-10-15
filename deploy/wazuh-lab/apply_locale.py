#!/usr/bin/env python3
"""VM: sudo python3 apply_locale.py <ru-RU.json>; локальный i18n, только dashboard.
Сохраняет backup compose/config, монтирует catalog для сохранения после recreate.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import yaml

root = Path("/home/service/wazuh-lab")
project = root / "upstream/single-node"
catalog = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
if not catalog.get("messages") or not all(isinstance(v, str) for v in catalog["messages"].values()):
    raise SystemExit("Invalid translation catalog")
backup = root / "locale-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup.mkdir(parents=True)
compose_path = project / "docker-compose.yml"
config_path = project / "config/wazuh_dashboard/opensearch_dashboards.yml"
for path in [compose_path, config_path]:
    shutil.copy2(path, backup / path.name)
locale_dir = root / "locale"
locale_dir.mkdir(exist_ok=True)
destination = locale_dir / "ru-RU.json"
destination.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
destination.chmod(0o644)
config = yaml.safe_load(config_path.read_text())
config["i18n.locale"] = "ru-RU"
config_path.write_text(yaml.safe_dump(config, sort_keys=False))
compose = yaml.safe_load(compose_path.read_text())
mount = str(destination) + ":/usr/share/wazuh-dashboard/src/translations/ru-RU.json:ro"
volumes = compose["services"]["wazuh.dashboard"]["volumes"]
if mount not in volumes:
    volumes.append(mount)
registration = locale_dir / "i18nrc.json"
registration.write_text(json.dumps({"translations": ["../../src/translations/ru-RU.json"]}), encoding="utf-8")
registration.chmod(0o644)
registration_mount = str(registration) + ":/usr/share/wazuh-dashboard/plugins/wazuhCore/.i18nrc.json:ro"
if registration_mount not in volumes:
    volumes.append(registration_mount)
compose_path.write_text(yaml.safe_dump(compose, sort_keys=False))
base = [str(root / "tools/docker-compose"), "-p", "msp-wazuh-lab"]
subprocess.run(base + ["config", "--quiet"], cwd=project, check=True)
subprocess.run(base + ["up", "-d", "--no-deps", "wazuh.dashboard"], cwd=project, check=True)
print("Russian local catalog applied; messages:", len(catalog["messages"]), "; rollback files:", backup)
