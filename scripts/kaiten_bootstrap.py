#!/usr/bin/env python3
"""
Подготовка базы в Kaiten для MSPShield: создаёт Space + Board + 6 колонок
и выводит board_id / column_id для копирования в backend/.env.

Запуск:
    KAITEN_DOMAIN=acme.kaiten.ru \
    KAITEN_API_TOKEN=xxx \
    python scripts/kaiten_bootstrap.py

Скрипт идемпотентен: если Space/Board с таким именем уже есть, он их
переиспользует и не плодит дубликаты. Колонки добавляются только те,
которых ещё нет.

Что создаётся:
- Space "MSPShield · Sales"
- Board "Lead Pipeline"
- 6 колонок (в порядке слева направо):
    1. Новая
    2. Первичный контакт
    3. Аудит
    4. КП
    5. Переговоры
    6. Закрыта · Win/Lost

После запуска: открой ссылку, выведенную скриптом, чтобы визуально
увидеть пустую доску — туда же будут попадать карточки из формы.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

import httpx

SPACE_TITLE = "MSPShield · Sales"
BOARD_TITLE = "Lead Pipeline"
COLUMNS = [
    "Новая",
    "Первичный контакт",
    "Аудит",
    "КП",
    "Переговоры",
    "Закрыта · Win/Lost",
]


def _api_base(domain: str) -> str:
    domain = domain.strip().rstrip("/")
    if "://" not in domain:
        domain = f"https://{domain}"
    return f"{domain}/api/latest"


def _fail(msg: str) -> None:
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def _check_auth(http: httpx.Client, base: str, headers: Dict[str, str]) -> None:
    """Проверяем связку domain+token ДО создания чего-либо.

    Так мы даём понятную ошибку вместо невнятного падения на /spaces.
    Дёргаем GET /users/current:
      - 200 → всё ок, печатаем, кто авторизован;
      - 401 → токен невалиден (перевыпусти в /profile/api-token);
      - 404 → неверный KAITEN_DOMAIN (такого workspace нет);
      - 403 → токен без доступа к workspace (выпусти из аккаунта-owner).
    """
    try:
        r = http.get(f"{base}/users/current", headers=headers)
    except Exception as exc:  # noqa: BLE001
        _fail(f"Не удалось подключиться к Kaiten ({base}): {exc}")
        return
    if 200 <= r.status_code < 300:
        data = r.json() if r.content else {}
        who = data.get("email") or data.get("username") or data.get("full_name") or data.get("id")
        print(f"✓ авторизация ок: {who}")
        return
    hints = {
        401: "невалидный токен — перевыпусти в https://<домен>.kaiten.ru/profile/api-token",
        403: "токен без доступа к workspace — выпусти токен из аккаунта-владельца (owner)",
        404: "неверный KAITEN_DOMAIN — такого workspace не существует, проверь поддомен",
    }
    _fail(f"GET /users/current: {r.status_code} — {hints.get(r.status_code, r.text[:200])}")


def _get_or_create_space(http: httpx.Client, base: str, headers: Dict[str, str]) -> Dict[str, Any]:
    r = http.get(f"{base}/spaces", headers=headers)
    if r.status_code != 200:
        _fail(f"GET /spaces: {r.status_code} {r.text[:200]}")
    spaces = r.json() or []
    if not isinstance(spaces, list):
        # Некоторые ответы Kaiten оборачивают данные; подстрахуемся.
        spaces = spaces.get("spaces", []) if isinstance(spaces, dict) else []
    for sp in spaces:
        if sp.get("title") == SPACE_TITLE:
            print(f"✓ space already exists: id={sp['id']} title={sp['title']!r}")
            return sp
    r = http.post(f"{base}/spaces", json={"title": SPACE_TITLE}, headers=headers)
    if r.status_code not in (200, 201):
        _fail(f"POST /spaces: {r.status_code} {r.text[:200]}")
    sp = r.json()
    print(f"✓ space created: id={sp['id']} title={sp['title']!r}")
    return sp


def _get_or_create_board(
    http: httpx.Client,
    base: str,
    headers: Dict[str, str],
    space_id: int,
) -> Dict[str, Any]:
    r = http.get(f"{base}/spaces/{space_id}/boards", headers=headers)
    if r.status_code == 200:
        for b in r.json() or []:
            if b.get("title") == BOARD_TITLE:
                print(f"✓ board already exists: id={b['id']} title={b['title']!r}")
                return b
    r = http.post(
        f"{base}/spaces/{space_id}/boards",
        json={"title": BOARD_TITLE},
        headers=headers,
    )
    if r.status_code not in (200, 201):
        _fail(f"POST boards: {r.status_code} {r.text[:200]}")
    b = r.json()
    print(f"✓ board created: id={b['id']} title={b['title']!r}")
    return b


def _existing_columns(
    http: httpx.Client,
    base: str,
    headers: Dict[str, str],
    board_id: int,
) -> List[Dict[str, Any]]:
    r = http.get(f"{base}/boards/{board_id}/columns", headers=headers)
    if r.status_code != 200:
        return []
    return r.json() or []


def _ensure_columns(
    http: httpx.Client,
    base: str,
    headers: Dict[str, str],
    board_id: int,
) -> List[Dict[str, Any]]:
    existing = _existing_columns(http, base, headers, board_id)
    by_title = {c.get("title"): c for c in existing}

    next_order = max((c.get("sort_order", 0) for c in existing), default=0) + 1

    for title in COLUMNS:
        if title in by_title:
            continue
        r = http.post(
            f"{base}/boards/{board_id}/columns",
            json={"title": title, "sort_order": next_order, "type": 1},
            headers=headers,
        )
        if r.status_code in (200, 201):
            col = r.json()
            print(f"✓ column created: {title!r} id={col.get('id')}")
            existing.append(col)
            next_order += 1
        else:
            print(
                f"! column {title!r} not created: {r.status_code} {r.text[:120]}",
                file=sys.stderr,
            )

    return _existing_columns(http, base, headers, board_id)


def main() -> int:
    domain = os.environ.get("KAITEN_DOMAIN", "").strip()
    token = os.environ.get("KAITEN_API_TOKEN", "").strip()
    if not domain or not token:
        _fail("Set KAITEN_DOMAIN and KAITEN_API_TOKEN env vars first.")

    base = _api_base(domain)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print(f"→ Kaiten base: {base}")
    with httpx.Client(timeout=15.0) as http:
        _check_auth(http, base, headers)
        space = _get_or_create_space(http, base, headers)
        board = _get_or_create_board(http, base, headers, space["id"])
        columns = _ensure_columns(http, base, headers, board["id"])

    first_col: Optional[Dict[str, Any]] = next(
        (c for c in columns if c.get("title") == COLUMNS[0]),
        columns[0] if columns else None,
    )

    print()
    print("─" * 60)
    print("Готово. Скопируй в backend/.env:")
    print()
    print(f"KAITEN_DOMAIN={domain}")
    print(f"KAITEN_BOARD_ID={board['id']}")
    if first_col:
        print(f"KAITEN_COLUMN_ID={first_col['id']}")
    print("─" * 60)
    web_domain = domain if "://" in domain else f"https://{domain}"
    print(
        f"Открой доску в браузере:\n  {web_domain.rstrip('/')}/space/{space['id']}/boards/{board['id']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
