#!/usr/bin/env python3
"""Проверяет машинно-проверяемые deployment и migration инварианты."""
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
for artifact in ("stalwart-etc.tar.gz", "stalwart-data.tar.gz", "vaultwarden-data.tar.gz", "max-session.tar.gz"):
    need("migration/restic-backup.sh", artifact)
    need("migration/restore-on-vm.sh", artifact)
    need("migration/migrate.ps1", artifact)
ban("migration/restic-backup.sh", '"/var/lib/docker/volumes"')
need("services/vm_watcher/watcher.ps1", "TcpClient")
ban("services/vm_watcher/watcher.ps1", "$env:YC_CONFIG_DIR")
if re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', read("services/vm_watcher/watcher.ps1")):
    errors.append("watcher.ps1: hardcoded IP")
# Документация может называть опасную команду как запрет; исполняемый uploader — нет.
ban("migration/migrate.ps1", "StrictHostKeyChecking=no")
need("scripts/deployment/preflight.sh", "BOM/CRLF")
need("README.md", "docs/README.md")
need("docs/README.md", "CLIENT_LIFECYCLE.md")
need("docs/training/README.md", "DEPLOYMENT_MIGRATION_LABS.md")

if errors:
    print("OPERATIONAL CONSISTENCY FAILED")
    for item in errors: print(" -", item)
    sys.exit(1)
print("OPERATIONAL CONSISTENCY OK")
