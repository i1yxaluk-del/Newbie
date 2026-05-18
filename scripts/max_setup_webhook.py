#!/usr/bin/env python3
"""
Регистрация webhook для бота MAX.

Что делает:
1. GET /me            — проверяет токен (печатает username и user_id бота).
2. GET /subscriptions — показывает текущие подписки.
3. DELETE /subscriptions — удаляет предыдущую подписку, если её URL
   отличается (MAX поддерживает только одну активную подписку на бота).
4. POST /subscriptions — подписывает бота на ваш URL.

Запуск:
    MAX_BOT_TOKEN=xxx \\
    MAX_WEBHOOK_URL=https://msp-oblako.ru/api/max/webhook \\
    MAX_WEBHOOK_SECRET=$(openssl rand -hex 32) \\
    python scripts/max_setup_webhook.py

Параметры:
    --token, --url, --secret — можно передать как CLI-аргументы.
    --dry-run                — только покажет, что собирается сделать.

Требования:
- MAX_WEBHOOK_URL должен быть HTTPS, порт 443, валидный TLS
  (не self-signed). Локально работать не будет.
- Backend должен уже отвечать 200 на POST /api/max/webhook
  (см. server.py). Если backend недоступен — MAX просто будет
  складывать события в очередь повторов (до 10 ретраев).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import httpx

MAX_API_BASE = os.environ.get("MAX_API_BASE", "https://platform-api.max.ru").rstrip("/")


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_me(token: str) -> Dict[str, Any]:
    r = httpx.get(f"{MAX_API_BASE}/me", headers=_headers(token), timeout=10.0)
    r.raise_for_status()
    return r.json()


def list_subscriptions(token: str) -> List[Dict[str, Any]]:
    r = httpx.get(
        f"{MAX_API_BASE}/subscriptions",
        headers=_headers(token),
        timeout=10.0,
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    data = r.json()
    return data.get("subscriptions", []) if isinstance(data, dict) else []


def delete_subscription(token: str, url: str) -> bool:
    r = httpx.delete(
        f"{MAX_API_BASE}/subscriptions",
        headers=_headers(token),
        params={"url": url},
        timeout=10.0,
    )
    return 200 <= r.status_code < 300


def create_subscription(
    token: str,
    url: str,
    secret: Optional[str] = None,
    update_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"url": url}
    if secret:
        body["secret"] = secret
    if update_types:
        body["update_types"] = update_types
    r = httpx.post(
        f"{MAX_API_BASE}/subscriptions",
        headers=_headers(token),
        json=body,
        timeout=10.0,
    )
    if not (200 <= r.status_code < 300):
        sys.stderr.write(f"create_subscription HTTP {r.status_code}: {r.text}\n")
        r.raise_for_status()
    return r.json() if r.content else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="MAX bot webhook setup")
    parser.add_argument("--token", default=os.environ.get("MAX_BOT_TOKEN", ""))
    parser.add_argument("--url", default=os.environ.get("MAX_WEBHOOK_URL", ""))
    parser.add_argument("--secret", default=os.environ.get("MAX_WEBHOOK_SECRET", ""))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="не вносить изменений, только показать план",
    )
    args = parser.parse_args()

    if not args.token:
        sys.stderr.write("ошибка: --token или MAX_BOT_TOKEN не задан\n")
        return 2
    if not args.url:
        sys.stderr.write("ошибка: --url или MAX_WEBHOOK_URL не задан\n")
        return 2
    if not args.url.startswith("https://"):
        sys.stderr.write("ошибка: URL должен быть HTTPS\n")
        return 2

    print(f"➜ MAX API: {MAX_API_BASE}")
    print(f"➜ Webhook URL: {args.url}")
    if args.secret:
        print(f"➜ Webhook secret: {'*' * 8}{args.secret[-4:]}")
    else:
        print("➜ Webhook secret: (не задан — небезопасно для prod)")

    me = get_me(args.token)
    print(f"\nБот: @{me.get('username', '?')}  (user_id={me.get('user_id')})")

    existing = list_subscriptions(args.token)
    if existing:
        print(f"\nТекущие подписки ({len(existing)}):")
        for sub in existing:
            print(f"  • {sub.get('url', '?')}  types={sub.get('update_types', 'all')}")
    else:
        print("\nТекущих подписок нет.")

    same_url_sub = next((s for s in existing if s.get("url") == args.url), None)
    if same_url_sub and not args.secret:
        print("\n✓ Подписка с таким URL уже есть, ничего не меняем.")
        return 0

    if args.dry_run:
        print("\n[dry-run] План:")
        for sub in existing:
            if sub.get("url") != args.url:
                print(f"  - удалить подписку {sub.get('url')}")
        print(f"  - создать подписку {args.url}")
        return 0

    for sub in existing:
        if sub.get("url") != args.url:
            ok = delete_subscription(args.token, sub.get("url", ""))
            print(f"  {'удалил' if ok else 'не удалил'} подписку {sub.get('url')}")

    created = create_subscription(
        args.token,
        url=args.url,
        secret=args.secret or None,
        update_types=["message_created", "message_callback", "bot_started"],
    )
    print(f"\n✓ Подписка создана: {created}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
