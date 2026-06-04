#!/usr/bin/env python3
"""
max_alerter/auth.py — interactive MAX authorization via CLI.

Run ONCE on the host (not in Docker) to create a SQLite session.
After that, mount the session as a volume into the container.

Usage:
    python auth.py --phone +79991234567 --session ./session/max.db
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_UA_DEVICE = "DESKTOP"
_UA_APP_VERSION = "25.12.13"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("max_auth")


async def _run(phone: str, session_path: Path) -> None:
    try:
        from pymax import Client  # type: ignore[import]
    except ImportError:
        log.error("pymax not installed. Run: pip install maxapi-python")
        sys.exit(1)

    session_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("Initializing client (phone: %s)", phone)
    log.info("Session: %s", session_path.resolve())

    client = Client(
        phone=phone,
        work_dir=str(session_path.parent),
        session_name=session_path.name,
    )

    @client.on_start()
    async def _on_start(c) -> None:
        uid = c.me.contact.id if c.me else "unknown"
        log.info("Authorized. MAX user_id=%s", uid)
        log.info("Session saved in %s", session_path.resolve())
        log.info("You can now run max_alerter in Docker.")
        await c.stop()

    await client.start()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MAX authorization (one-time, creates SQLite session)"
    )
    parser.add_argument(
        "--phone",
        required=True,
        help="Phone number in format +79991234567",
    )
    parser.add_argument(
        "--session",
        default="./session/max.db",
        help="Path to session file (default: ./session/max.db)",
    )
    args = parser.parse_args()

    asyncio.run(_run(phone=args.phone, session_path=Path(args.session)))


if __name__ == "__main__":
    main()
