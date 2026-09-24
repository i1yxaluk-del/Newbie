#!/usr/bin/env python3
"""Ручная авторизация MAX userbot.

Где запускать: только интерактивно внутри `msp-max-alerter`.
Без `--authorize` скрипт лишь проверяет `/session/max.db` и не отправляет SMS.
Номер телефона читается из MAX_PHONE; персональные значения в коде запрещены.
"""
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
log = logging.getLogger("max_auth")
PHONE = os.environ.get("MAX_PHONE", "").strip()
SESSION_DIR = Path(os.environ.get("MAX_SESSION_DIR", "/session"))
SESSION_NAME = os.environ.get("MAX_SESSION_NAME", "max.db").strip()


async def authorize() -> None:
    """Удаляет только старую нерабочую сессию и запускает ручной ввод кода."""
    if not PHONE:
        raise RuntimeError("MAX_PHONE не задан в окружении контейнера")
    from pymax import Client
    session_file = SESSION_DIR / SESSION_NAME
    if session_file.exists():
        session_file.unlink()
        log.info("Старая сессия удалена: %s", session_file)
    client = Client(phone=PHONE, work_dir=str(SESSION_DIR), session_name=SESSION_NAME)

    @client.on_start()
    async def on_start(current_client):
        user_id = current_client.me.contact.id if current_client.me else "unknown"
        log.info("Авторизация успешна, user_id=%s", user_id)
        await current_client.stop()

    await client.start()


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка или ручная авторизация MAX")
    parser.add_argument("--authorize", action="store_true", help="явно запросить SMS и ввести код")
    args = parser.parse_args()
    session_file = SESSION_DIR / SESSION_NAME
    if not args.authorize:
        if session_file.is_file() and session_file.stat().st_size > 0:
            log.info("Сессия существует: %s; SMS не отправлялась", session_file)
            return 0
        log.error("Сессия отсутствует: %s; используйте --authorize вручную", session_file)
        return 2
    try:
        asyncio.run(authorize())
        return 0
    except Exception as exc:  # оператор должен увидеть понятную причину и решить, повторять ли SMS.
        log.error("Авторизация не выполнена: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
