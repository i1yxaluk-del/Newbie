#!/usr/bin/env python3
"""Проверяет, что deployment lessons реализованы в коде, а не только описаны."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
def read(path: str) -> str: return (ROOT / path).read_text(encoding="utf-8")
def need(path: str, value: str) -> None:
    if value not in read(path): errors.append(f"{path}: нет {value!r}")
def ban(path: str, value: str) -> None:
    if value in read(path): errors.append(f"{path}: запрещено {value!r}")

if (ROOT / "deploy/yandex/.deploy-state.json").exists(): errors.append(".deploy-state.json не должен быть tracked")
need("deploy/yandex/monitoring/docker-compose.override.yml", "SMTP_AUTH_PASSWORD")
need("migration/restic-backup.sh", "stalwart-etc.tar.gz")
need("migration/restic-backup.sh", "max-session.tar.gz")
ban("migration/restic-backup.sh", '"/var/lib/docker/volumes"')
need("migration/restore-on-vm.sh", "stalwart-data.tar.gz")
need("services/vm_watcher/watcher.ps1", "TcpClient")
ban("services/vm_watcher/watcher.ps1", "$env:YC_CONFIG_DIR")
if re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', read("services/vm_watcher/watcher.ps1")): errors.append("watcher.ps1: hardcoded IP")
for path in ("migration/README.md", "migration/migrate.ps1"):
    ban(path, "StrictHostKeyChecking=no")
for path in ("scripts/deployment/preflight.sh", "migration/restic-backup.sh", "migration/restore-on-vm.sh"):
    for marker in ("Назначение:", "Где запускать:", "Откат:"):
        need(path, marker)
for path in ("README.md", "docs/README.md", "docs/deployment/README.md"):
    for target in re.findall(r"\[[^]]+\]\(([^)#]+)", read(path)):
        if "://" in target: continue
        resolved = ((ROOT / path).parent / target).resolve()
        if not resolved.exists(): errors.append(f"{path}: битая ссылка {target}")

if errors:
    print("OPERATIONAL CONSISTENCY FAILED")
    for item in errors: print(" -", item)
    sys.exit(1)
print("OPERATIONAL CONSISTENCY OK")
