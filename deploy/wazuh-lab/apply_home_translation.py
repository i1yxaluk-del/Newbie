#!/usr/bin/env python3
"""VM: mount version-checked template + local JS for hard-coded Wazuh home labels.
Backup before change; recreate dashboard only. No CSP relaxation.
"""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import yaml

root = Path("/home/service/wazuh-lab")
project = root / "upstream/single-node"
compose_path = project / "docker-compose.yml"
config = yaml.safe_load(compose_path.read_text())
if config["services"]["wazuh.dashboard"]["image"] != "wazuh/wazuh-dashboard:4.14.5":
    raise SystemExit("Template patch requires review for this image version")
backup = root / "locale-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup.mkdir(parents=True)
shutil.copy2(compose_path, backup / compose_path.name)
locale = root / "locale"
source = "/usr/share/wazuh-dashboard/src/core/server/rendering/views/template.js"
original = subprocess.check_output(["docker", "exec", "msp-wazuh-lab-wazuh.dashboard-1", "cat", source], text=True)
(backup / "template.js").write_text(original)
marker = 'src: bootstrapScriptUrl'
if marker not in original:
    raise SystemExit("Unexpected rendering template")
if "msp-wazuh-home-ru.js" not in original:
    original = original.replace(marker, 'src: `${uiPublicUrl}/msp-wazuh-home-ru.js`\n  }), /*#__PURE__*/_react.default.createElement("script", {\n    ' + marker, 1)
template = locale / "template.js"
template.write_text(original)
script = locale / "wazuh-home-ru.js"
shutil.copyfile(sys.argv[1], script)
for path in [template, script]:
    path.chmod(0o644)
volumes = config["services"]["wazuh.dashboard"]["volumes"]
for mount in [f"{template}:{source}:ro", f"{script}:/usr/share/wazuh-dashboard/src/core/server/core_app/assets/msp-wazuh-home-ru.js:ro"]:
    if mount not in volumes:
        volumes.append(mount)
compose_path.write_text(yaml.safe_dump(config, sort_keys=False))
base = [str(root / "tools/docker-compose"), "-p", "msp-wazuh-lab"]
subprocess.run(base + ["config", "--quiet"], cwd=project, check=True)
subprocess.run(base + ["up", "-d", "--no-deps", "wazuh.dashboard"], cwd=project, check=True)
print("Home labels translation applied; backup:", backup)
