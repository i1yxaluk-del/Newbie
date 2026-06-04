#!/usr/bin/env python3
"""
max_alerter/auth.py — интерактивная авторизация в MAX через CLI.

Запускается ОДИН РАЗ на хосте (не в Docker) для создания SQLite-сессии.
После этого сессия монтируется в контейнер как volume.

Использование:
python auth.py --phone +79991234567 --session ./session/max.db

Повторный запуск с той же сессией — авторизация не нужна, просто проверка.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Скрываем автоматизацию: стандартный user-agent десктопного клиента
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
    log.error("pymax не установлен. Запустите: pip install maxapi-python")
    sys.exit(1)

session_path.parent.mkdir(parents=True, exist_ok=True)

log.info("Инициализация клиента (телефон: %s)", phone)
log.info("Сессия: %s", session_path.resolve())

client = Client(
    phone=phone,
    work_dir=str(session_path.parent),
    session_name=session_path.name,
)

@client.on_start()
async def _on_start(c: Client) -> None:  # noqa: ANN001
    uid = c.me.contact.id if c.me else "unknown"
    log.info("✓ Авторизован. MAX user_id=%s", uid)
    log.info("Сессия сохранена в %s", session_path.resolve())
    log.info("Можно запускать max_alerter в Docker.")
    await c.stop()

await client.start()


def main() -> None:
parser = argparse.ArgumentParser(
    description="Авторизация в MAX (один раз, создаёт SQLite-сессию)"
)
parser.add_argument(
    "--phone",
    required=True,
    help="Номер телефона в формате +79991234567",
)
parser.add_argument(
    "--session",
    default="./session/max.db",
    help="Путь к файлу сессии (default: ./session/max.db)",
)
args = parser.parse_args()

asyncio.run(_run(phone=args.phone, session_path=Path(args.session)))


if __name__ == "__main__":
main()
