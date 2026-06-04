"""
max_alerter/sender.py — отправка сообщений в MAX через pymax Client.

Держит одно постоянное TCP-соединение (reconnect встроен в pymax).
При сбое доставки — fallback в Telegram + запись в failed_alerts.log.

Переменные окружения:
MAX_PHONE        — номер телефона аккаунта MAX (+79991234567)
MAX_SESSION_DIR  — директория с SQLite-сессией (default: /session)
MAX_SESSION_NAME — имя файла сессии (default: max.db)
TG_BOT_TOKEN     — токен Telegram-бота для fallback (опционально)
TG_CHAT_ID       — chat_id Telegram для fallback (опционально)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("max_alerter.sender")

# ── конфиг из env ──────────────────────────────────────────────────────────────
MAX_PHONE: str = os.environ.get("MAX_PHONE", "")
MAX_SESSION_DIR: Path = Path(os.environ.get("MAX_SESSION_DIR", "/session"))
MAX_SESSION_NAME: str = os.environ.get("MAX_SESSION_NAME", "max.db")
TG_BOT_TOKEN: str = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID: str = os.environ.get("TG_CHAT_ID", "")

FAILED_LOG: Path = Path(os.environ.get("FAILED_LOG", "/data/failed_alerts.log"))

# ── глобальный клиент (singleton) ──────────────────────────────────────────────
_client: Optional[object] = None
_client_lock = asyncio.Lock()


async def get_client():  # noqa: ANN201
    """Возвращает запущенный pymax Client (создаёт при первом вызове)."""
    global _client  # noqa: PLW0603

    async with _client_lock:
        if _client is not None:
            return _client

        try:
            from pymax import Client  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("pymax не установлен: pip install maxapi-python") from exc

        if not MAX_PHONE:
            raise RuntimeError("MAX_PHONE не задан в переменных окружения")

        MAX_SESSION_DIR.mkdir(parents=True, exist_ok=True)

        log.info("Запуск pymax Client (телефон=%s, сессия=%s/%s)",
                 MAX_PHONE, MAX_SESSION_DIR, MAX_SESSION_NAME)

        client = Client(
            phone=MAX_PHONE,
            work_dir=str(MAX_SESSION_DIR),
            session_name=MAX_SESSION_NAME,
        )

        # Запускаем в фоне — client.start() держит event loop
        loop = asyncio.get_event_loop()
        ready = asyncio.Event()

        @client.on_start()
        async def _on_start(c) -> None:  # noqa: ANN001
            uid = c.me.contact.id if c.me else "unknown"
            log.info("MAX клиент готов. user_id=%s", uid)
            ready.set()

        loop.create_task(client.start())
        await asyncio.wait_for(ready.wait(), timeout=30)

        _client = client
        return _client


async def send_to_max(chat_id: int, text: str) -> bool:
    """
    Отправляет text в MAX-чат chat_id.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        client = await get_client()
        await client.send_message(chat_id=chat_id, text=text)
        log.info("MAX ✓ chat_id=%s len=%d", chat_id, len(text))
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("MAX ✗ chat_id=%s error=%s", chat_id, exc)
        return False


async def _fallback_telegram(text: str) -> None:
    """Fallback: шлём в Telegram если MAX недоступен."""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        log.warning("Telegram fallback не настроен (TG_BOT_TOKEN/TG_CHAT_ID пусты)")
        return

    try:
        import httpx  # type: ignore[import]

        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": f"⚠️ MAX недоступен, fallback:\n\n{text}",
            "parse_mode": "HTML",
        }
        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.post(url, json=payload)
            r.raise_for_status()
        log.info("Telegram fallback ✓")
    except Exception as exc:  # noqa: BLE001
        log.error("Telegram fallback ✗ %s", exc)


def _write_failed_log(chat_id: int, text: str, error: str) -> None:
    """Пишем недоставленный алерт в файл для последующего разбора."""
    try:
        FAILED_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with FAILED_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] chat_id={chat_id} error={error!r}\n{text}\n---\n")
    except Exception as exc:  # noqa: BLE001
        log.error("Не удалось записать failed_alerts.log: %s", exc)


async def deliver(chat_id: int, text: str) -> None:
    """
    Основная точка входа: доставить алерт.
    1. Пробуем MAX.
    2. При неудаче — Telegram fallback + запись в failed_alerts.log.
    """
    ok = await send_to_max(chat_id, text)
    if not ok:
        _write_failed_log(chat_id, text, "send_to_max failed")
        await _fallback_telegram(text)
