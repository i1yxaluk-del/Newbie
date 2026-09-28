#!/usr/bin/env python3
"""Ручная авторизация MAX userbot.

Где запускать: только интерактивно внутри `msp-max-alerter`.
Без `--authorize` скрипт лишь проверяет `/session/max.db` и не отправляет SMS.
Номер телефона читается из MAX_PHONE; персональные значения в коде запрещены.

Флоу авторизации:
  1) MAX отправляет SMS-код — скрипт спросит его в консоли
     (неинтерактивно: переменная окружения MAX_SMS_CODE);
  2) если у аккаунта включён пароль 2FA — MAX запросит пароль,
     скрипт спросит его скрытым вводом (getpass; неинтерактивно: MAX_PASSWORD).
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


class _EnvSmsCodeProvider:
    """SmsCodeProvider с фиксированным кодом из окружения (неинтерактивный режим)."""

    def __init__(self, code: str) -> None:
        self._code = code

    async def get_code(self, phone: str) -> str:
        return self._code


class _EnvPasswordProvider:
    """PasswordProvider с фиксированным паролем из окружения (неинтерактивный режим)."""

    def __init__(self, password: str) -> None:
        self._password = password

    async def get_password(self, hint: str | None = None) -> str:
        return self._password


async def authorize() -> None:
    """Удаляет только старую нерабочую сессию и запускает ручной ввод кода и 2FA-пароля."""
    if not PHONE:
        raise RuntimeError("MAX_PHONE не задан в окружении контейнера")
    from pymax import (
        Client,
        ConsolePasswordProvider,
        ConsoleSmsCodeProvider,
        SmsAuthFlow,
    )

    env_code = os.environ.get("MAX_SMS_CODE", "").strip()
    env_password = os.environ.get("MAX_PASSWORD", "").strip()
    if env_code:
        log.info("SMS-код берётся из MAX_SMS_CODE (неинтерактивный режим)")
        code_provider = _EnvSmsCodeProvider(env_code)
    else:
        code_provider = ConsoleSmsCodeProvider()
    if env_password:
        log.info("Пароль 2FA берётся из MAX_PASSWORD (неинтерактивный режим)")
        password_provider = _EnvPasswordProvider(env_password)
    else:
        password_provider = ConsolePasswordProvider()

    session_file = SESSION_DIR / SESSION_NAME
    if session_file.exists():
        session_file.unlink()
        log.info("Старая сессия удалена: %s", session_file)

    flow = SmsAuthFlow(code_provider, password_provider)
    client = Client(
        phone=PHONE,
        work_dir=str(SESSION_DIR),
        session_name=SESSION_NAME,
        auth_flow=flow,
    )

    log.info(
        "Запрашиваю код у MAX. Если у аккаунта включён 2FA — после кода потребуется пароль (ввод скрыт)."
    )

    @client.on_start()
    async def on_start(current_client):
        user_id = current_client.me.contact.id if current_client.me else "unknown"
        log.info("Авторизация успешна, user_id=%s", user_id)
        log.info("Сессия сохранена: %s", session_file)
        await current_client.stop()

    await client.start()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Проверка или ручная авторизация MAX (SMS-код + пароль 2FA)"
    )
    parser.add_argument("--authorize", action="store_true", help="явно запросить SMS и ввести код/пароль")
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
