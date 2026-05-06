#!/usr/bin/env python3
"""
Создаёт 3 тестовые заявки через локальный API — для проверки админки и
интеграции с CRM. Все заявки помечены `source=test`, чтобы их легко было
отфильтровать и удалить.

Запуск:
    BACKEND_URL=http://localhost:8001 python scripts/seed_test_lead.py

В админке: фильтр source=test → массовое удаление через API.
В Kaiten:  поиск по тегу/тексту "[test]" — все три карточки.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001").rstrip("/")

SAMPLES = [
    {
        "name": "TEST · Иван Петров",
        "company": "TEST · ООО Альфа",
        "contact": "+7 999 1111111",
        "email": "test1@example.com",
        "servers": "1-3",
        "tariff": "bronze",
        "message": "[test seed] заявка для проверки админки и CRM",
        "consent": True,
        "source": "test",
    },
    {
        "name": "TEST · Мария Сидорова",
        "company": "TEST · ИП Бета",
        "contact": "@maria_test",
        "email": "test2@example.com",
        "servers": "4-10",
        "tariff": "silver",
        "message": "[test seed] средняя компания, AD + Linux",
        "consent": True,
        "source": "test",
    },
    {
        "name": "TEST · Сергей Иванов",
        "company": "TEST · ООО Гамма",
        "contact": "+7 999 2222222",
        "email": "test3@example.com",
        "servers": "30+",
        "tariff": "gold",
        "message": "[test seed] корпоративный сегмент, SLA-критично",
        "consent": True,
        "source": "test",
    },
]


def main() -> int:
    print(f"→ POST {BACKEND_URL}/api/leads (×{len(SAMPLES)})")
    ok = 0
    with httpx.Client(timeout=15.0) as http:
        for i, payload in enumerate(SAMPLES, start=1):
            try:
                r = http.post(f"{BACKEND_URL}/api/leads", json=payload)
                if 200 <= r.status_code < 300:
                    data = r.json()
                    print(f"  [{i}/{len(SAMPLES)}] ✓ {data.get('id')} · {payload['company']}")
                    ok += 1
                else:
                    print(
                        f"  [{i}/{len(SAMPLES)}] ✗ {r.status_code} {r.text[:120]}",
                        file=sys.stderr,
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"  [{i}/{len(SAMPLES)}] ✗ {exc}", file=sys.stderr)

    print()
    print("─" * 60)
    print(f"Готово: {ok}/{len(SAMPLES)} заявок отправлено в {datetime.now().isoformat(timespec='seconds')}")
    print()
    print("Где смотреть:")
    print(f"  Админка:  /admin → войди по ADMIN_TOKEN, фильтр source=test")
    print(f"  Kaiten:   доска Lead Pipeline → колонка «Новая», карточки с префиксом [test]")
    print(f"  Telegram: придёт 3 уведомления (если настроен бот)")
    return 0 if ok == len(SAMPLES) else 1


if __name__ == "__main__":
    sys.exit(main())
