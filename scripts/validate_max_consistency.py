#!/usr/bin/env python3
"""CI-gate против возврата старого Telegram/MAX и небезопасного deploy."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(path: str, value: str) -> None:
    if value not in text(path):
        errors.append(f"{path}: отсутствует {value!r}")

def forbid(path: str, value: str) -> None:
    if value in text(path):
        errors.append(f"{path}: запрещён старый фрагмент {value!r}")

for marker in ("my.telegram.org/apps", "Telethon", "API_HASH", "session.session", "порт `8080`"):
    forbid("docs/MAX_SETUP.md", marker)
require("docs/MAX_SETUP.md", "docker exec -it msp-max-alerter python -m max_alerter.auth --authorize")
require("docs/MAX_SETUP.md", "/session/max.db")
require("services/max_alerter/requirements.txt", "maxapi-python==2.1.2")
require("services/max_alerter/sender.py", 'url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"')
forbid("services/max_alerter/sender.py", 'f"{{https://api.telegram.org')
require("services/max_alerter/webhook.py", "HTTP_503_SERVICE_UNAVAILABLE")
require("deploy/yandex/monitoring/alertmanager/alertmanager.yml.tmpl", "http://msp-max-alerter:9095/alert")
forbid("deploy/yandex/monitoring/alertmanager/alertmanager.yml.tmpl", "msp-backend")
compose = text("deploy/yandex/monitoring/docker-compose.yml")
if re.search(r"MAX_PHONE:\s*[\"']?\+?\d{10,}", compose):
    errors.append("monitoring compose: MAX_PHONE захардкожен")
if re.search(r"MAX_CHAT_ID:\s*[\"']?-\d{6,}", compose):
    errors.append("monitoring compose: MAX_CHAT_ID захардкожен")
for path in ("migration/README.md", "migration/migrate.ps1", "migration/restore-on-vm.sh"):
    forbid(path, "StrictHostKeyChecking=no")
    forbid(path, "msp-mongo-1")
if re.search(r"YCAJ[A-Za-z0-9_-]{12,}", text("migration/README.md")):
    errors.append("migration/README.md: похожий на access key фрагмент")

if errors:
    print("MAX consistency FAILED:")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)
print("MAX consistency OK")
