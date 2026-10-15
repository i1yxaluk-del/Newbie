#!/usr/bin/env python3
"""VM: sudo python3 start.py — запуск только выделенного проекта msp-wazuh-lab.
Меняет vm.max_map_count (требование indexer), не перезапускает Docker/чужие services.
"""
from pathlib import Path
import subprocess

project = Path("/home/service/wazuh-lab/upstream/single-node")
if not (project / "docker-compose.yml").is_file():
    raise SystemExit("Сначала prepare.py")
setting = Path("/etc/sysctl.d/90-msp-wazuh-lab.conf")
if setting.exists() and "Wazuh lab indexer requirement" not in setting.read_text():
    raise SystemExit("Чужая sysctl настройка: нужен review")
setting.write_text("# Wazuh lab indexer requirement\nvm.max_map_count=262144\n")
subprocess.run(["/sbin/sysctl", "-w", "vm.max_map_count=262144"], check=True)
base = ["/home/service/wazuh-lab/tools/docker-compose", "-p", "msp-wazuh-lab"]
subprocess.run(base + ["config", "--quiet"], cwd=project, check=True)
subprocess.run(base + ["-f", "generate-indexer-certs.yml", "run", "--rm", "generator"], cwd=project, check=True)
# bind dirs не заполняются образом автоматически, в отличие от обычного named volume.
# Обеспечить ownership indexer до старта, остальные initialize entrypoints — root.
subprocess.run(["chown", "-R", "1000:1000", "/home/service/wazuh-lab/data/wazuh-indexer-data"], check=True)
subprocess.run(base + ["up", "-d"], cwd=project, check=True)
print("Started training project; verify health, then install local rules and generate events")
