"""Регрессии: никаких фоновых SMS и Telegram только после отказа MAX."""
import asyncio
from pathlib import Path

from max_alerter import sender


def test_missing_session_does_not_start_pymax(monkeypatch, tmp_path):
    monkeypatch.setattr(sender, "MAX_PHONE", "+70000000000")
    monkeypatch.setattr(sender, "MAX_SESSION_DIR", Path(tmp_path))
    monkeypatch.setattr(sender, "MAX_SESSION_NAME", "missing.db")
    try:
        asyncio.run(sender.get_client())
    except RuntimeError as exc:
        assert "manual authorization required" in str(exc)
    else:
        raise AssertionError("missing session must not start pymax")


def test_max_failure_uses_fallback(monkeypatch, tmp_path):
    telegram, email = [], []
    async def failed_max(*_args): return False
    async def telegram_send(chat_id, text): telegram.append((chat_id, text)); return True
    async def email_send(subject, text): email.append((subject, text)); return True
    monkeypatch.setattr(sender, "send_to_max", failed_max)
    monkeypatch.setattr(sender, "send_to_telegram", telegram_send)
    monkeypatch.setattr(sender, "send_to_email", email_send)
    monkeypatch.setattr(sender, "TG_BOT_TOKEN", "token")
    monkeypatch.setattr(sender, "TG_CHAT_ID", "chat")
    monkeypatch.setattr(sender, "FAILED_LOG", tmp_path / "failed.log")
    assert asyncio.run(sender.deliver_max(1, "test")) is False
    assert telegram and email


def test_telegram_url_has_no_braces(monkeypatch):
    captured = []
    class Response:
        def raise_for_status(self): pass
    class Client:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def post(self, url, json): captured.append(url); return Response()
    monkeypatch.setattr(sender.httpx, "AsyncClient", Client)
    monkeypatch.setattr(sender, "TG_BOT_TOKEN", "abc")
    assert asyncio.run(sender.send_to_telegram("1", "x"))
    assert captured == ["https://api.telegram.org/botabc/sendMessage"]
