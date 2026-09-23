#!/usr/bin/env python3
"""Проверяет критичные коммерческие обещания в текущих документах.

Назначение: не дать старой цене Gold или обещанию круглосуточного инженера
вернуться в лендинг, README и новые договорные шаблоны.

Где запускать: из корня репозитория командой
`python scripts/validate_business_consistency.py`.

Побочные эффекты: отсутствуют; скрипт только читает файлы.
Откат: не требуется. Если проверка упала, исправьте источник расхождения,
а не удаляйте правило без согласования владельца продукта.
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CRITICAL_TEXT_FILES = [
    ROOT / "README.md",
    ROOT / "technical/README.md",
    ROOT / "technical/BUSINESS_MODEL.md",
    ROOT / "docs/PRICING_SOURCE_OF_TRUTH.md",
    ROOT / "docs/sales/templates/kp_template.md",
    ROOT / "contracts/README.md",
    ROOT / "contracts/canonical/TARIFFS_SLA.md",
    ROOT / "frontend/public/docs/offer.html",
]

errors = []
for path in CRITICAL_TEXT_FILES:
    # UTF-8 задаём явно, чтобы проверка одинаково работала на Linux и Windows.
    text = path.read_text(encoding="utf-8")
    if re.search(r"Gold.{0,80}85[\s\u00a0]000", text, re.IGNORECASE | re.DOTALL):
        errors.append(f"{path.relative_to(ROOT)}: найдена отменённая цена Gold 85 000 ₽")
    if "безлимит" in text.lower() and "вместо безлимита" not in text.lower():
        errors.append(f"{path.relative_to(ROOT)}: найдено опасное обещание безлимита")

landing_path = ROOT / "frontend/src/content/landing.ru.json"
landing = json.loads(landing_path.read_text(encoding="utf-8"))
prices = {plan["id"]: plan["price"] for plan in landing["pricing"]["plans"]}
expected = {"bronze": "25 000", "silver": "50 000", "gold": "120 000"}
if prices != expected:
    errors.append(f"landing.ru.json: цены {prices}, ожидались {expected}")

footnote = landing["pricing"].get("pricingFootnote", "")
if "не равен круглосуточному дежурству" not in footnote:
    errors.append("landing.ru.json: нет явного различия мониторинга и дежурства")

if errors:
    print("Проверка коммерческой согласованности: ОШИБКА")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Проверка коммерческой согласованности: OK")
