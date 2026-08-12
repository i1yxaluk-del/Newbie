"""Regression tests for no-SMS MAX startup and independent channel fallback."""
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


def test_max_failure_notifies_email(monkeypatch):
    notices = []

    async def failed_max(*_args):
        return False

    async def email(subject, text):
        notices.append((subject, text))
        return True

    monkeypatch.setattr(sender, "send_to_max", failed_max)
    monkeypatch.setattr(sender, "send_to_email", email)
    monkeypatch.setattr(sender, "TG_BOT_TOKEN", "")
    asyncio.run(sender.deliver_max(1, "test"))
    assert notices and "MAX channel unavailable" in notices[0][0]
