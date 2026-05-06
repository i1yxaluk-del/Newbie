"""
Admin authentication
====================

Два способа аутентификации, оба валидны:

1. Лонг-лайв токен `X-Admin-Token: <ADMIN_TOKEN>` — back-compat,
   удобен для curl / cron / health-проб.
2. JWT-сессия. Пользователь вводит ADMIN_TOKEN как пароль на `/admin`,
   получает JWT (24 ч), фронт хранит в localStorage. Все последующие
   запросы — `Authorization: Bearer <jwt>`.

Зачем оба: токен в header'е каждого запроса работает «из коробки», но не
переживает перезагрузку страницы. JWT даёт человеческий UX логина без
ввода secret-токена при каждом действии в админке.
"""
from __future__ import annotations

import os
import time
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, status

JWT_ALG = "HS256"


def _admin_token() -> str:
    """Читаем ADMIN_TOKEN динамически — на момент import'а .env ещё не загружен."""
    return os.environ.get("ADMIN_TOKEN", "")


def _jwt_secret() -> str:
    return os.environ.get("JWT_SECRET") or _admin_token() or "unconfigured"


def _jwt_ttl() -> int:
    return int(os.environ.get("JWT_TTL_SECONDS", str(24 * 3600)))


# Back-compat re-export: модули, импортирующие `ADMIN_TOKEN`, получат строку
# на момент чтения. На import'е она пустая — это нормально, т.к. .env
# подгружается в server.py до первого запроса.
class _LazyToken:
    def __bool__(self) -> bool:
        return bool(_admin_token())

    def __eq__(self, other) -> bool:  # noqa: D401
        return _admin_token() == other

    def __str__(self) -> str:
        return _admin_token()


ADMIN_TOKEN = _LazyToken()
JWT_TTL_SECONDS = _jwt_ttl()


def issue_admin_jwt() -> tuple[str, int]:
    """Возвращает (token, expires_at_unix)."""
    now = int(time.time())
    exp = now + _jwt_ttl()
    payload = {"sub": "admin", "iat": now, "exp": exp}
    token = jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALG)
    return token, exp


def verify_admin_jwt(token: str) -> bool:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALG])
        return payload.get("sub") == "admin"
    except jwt.PyJWTError:
        return False


def require_admin(
    x_admin_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
) -> None:
    """503 если ADMIN_TOKEN не настроен, 401 при невалидной аутентификации."""
    admin_token = _admin_token()
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin access not configured",
        )

    if x_admin_token and x_admin_token == admin_token:
        return

    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
        if verify_admin_jwt(bearer):
            return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# Re-exported for FastAPI Depends
AdminDep = Depends(require_admin)
