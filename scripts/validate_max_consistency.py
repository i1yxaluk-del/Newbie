#!/usr/bin/env python3
"""CI-gate канонического MAX userbot и безопасного deployment.

Исторические термины разрешены в разделе migration/legacy, но активные
команды, route и код должны соответствовать одному production-контуру.
"""
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
        errors.append(f"{path}: запрещён фрагмент {value!r}")

require("docs/MAX_SETUP.md", "docker exec -it msp-max-alerter python -m max_alerter.auth --authorize")
require("docs/MAX_SETUP.md", "/session/max.db")
require("docs/MAX_SETUP.md", "Alertmanager → POST http://msp-max-alerter:9095/alert")
require("services/max_alerter/requirements.txt", "maxapi-python==2.1.2")
require("services/max_alerter/sender.py", 'url = "https://api.telegram.org/bot" + TG_BOT_TOKEN + "/sendMessage"')
forbid("services/max_alerter/sender.py", 'f"{{https://api.telegram.org')
require("services/max_alerter/webhook.py", "HTTP_503_SERVICE_UNAVAILABLE")
require("deploy/yandex/monitoring/alertmanager/alertmanager.yml.tmpl", "http://msp-max-alerter:9095/alert")
forbid("deploy/yandex/monitoring/alertmanager/alertmanager.yml.tmpl", "msp-backend")
compose = text("deploy/yandex/monitoring/docker-compose.yml")
if re.search(r"MAX_PHONE:\s*[\"']?\+?\d{10,}", compose):
    errors.append("monitoring compose: MAX_PHONE захардкожен")
if re.search(r"MAX_CHAT_ID:\s*[\"']?-\d{6,}", compose):
    errors.append("monitoring compose: MAX_CHAT_ID захардкожен")
require("deploy/yandex/monitoring/docker-compose.yml", "127.0.0.1:9095:9095")
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
