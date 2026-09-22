#!/usr/bin/env python3
"""
max_alerter/auth.py — interactive MAX authorization.

Run inside container with -it (interactive TTY):

    docker exec -it msp-max-alerter python -m max_alerter.auth --authorize

1) MAX sends SMS to +79990703823
2) Script waits for you to type the code
3) Session saved to /session/max.db

Without --authorize this command only checks the persisted session file and never sends SMS.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("max_auth")

_PHONE = "+79990703823"
_SESSION_DIR = "/session"
_SESSION_NAME = "max.db"


async def _auth() -> None:
    from pymax import Client

    sf = Path(_SESSION_DIR) / _SESSION_NAME
    if sf.exists():
        sf.unlink()
        log.info("Deleted old session %s", sf)

    client = Client(
        phone=_PHONE,
        work_dir=_SESSION_DIR,
        session_name=_SESSION_NAME,
    )

    @client.on_start()
    async def _on_start(c):
        uid = c.me.contact.id if c.me else "unknown"
        log.info("Authorization OK! user_id=%s", uid)
        log.info("Session saved: %s/%s", _SESSION_DIR, _SESSION_NAME)
        await c.stop()

    log.info("Starting MAX auth for %s", _PHONE)
    log.info("SMS will be sent. Type the code when prompted.")
    try:
        await client.start()
    except Exception as e:
        log.error("Auth failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check or manually authorize MAX")
    parser.add_argument("--authorize", action="store_true", help="explicitly send SMS and request a code")
    args = parser.parse_args()
    session_file = Path(_SESSION_DIR) / _SESSION_NAME
    if not args.authorize:
        if session_file.is_file() and session_file.stat().st_size:
            log.info("MAX session file exists: %s (no SMS sent)", session_file)
            sys.exit(0)
        log.error("MAX session missing: %s (no SMS sent; use --authorize manually)", session_file)
        sys.exit(2)
    asyncio.run(_auth())
