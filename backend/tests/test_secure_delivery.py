"""Production delivery regressions: no MongoDB, SMTP or HTTP network calls."""
import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "mspshield_test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import secure_server as production
from integrations import max as max_int, telegram, email


@pytest.mark.parametrize("channel,module", [
    ("telegram", telegram), ("email", email), ("max", max_int),
])
def test_failed_delivery_is_not_acknowledged(monkeypatch, channel, module):
    monkeypatch.setattr(module, "send", AsyncMock(return_value=False))
    assert asyncio.run(production._send_channel(channel, {"id": "test"})) is False


def test_failed_outbox_channel_remains_pending(monkeypatch):
    job = {"lead_id": "test", "payload": {"id": "test"}, "pending": ["max"], "attempts": 0}
    outbox = SimpleNamespace(find_one=AsyncMock(return_value=job),
                             update_one=AsyncMock(), delete_one=AsyncMock())
    monkeypatch.setattr(production.server, "db", SimpleNamespace(crm_outbox=outbox))
    monkeypatch.setattr(production, "_send_channel", AsyncMock(return_value=False))
    asyncio.run(production._process_delivery("test"))
    outbox.delete_one.assert_not_called()
    update = outbox.update_one.call_args.args[1]
    assert update["$set"]["attempts"] == 1
    assert "max" in update["$set"]["last_errors"]
    assert all("$pull" not in call.args[1] for call in outbox.update_one.call_args_list)


def test_enqueue_does_not_send_concurrently_with_poller(monkeypatch):
    outbox = SimpleNamespace(update_one=AsyncMock())
    leads = SimpleNamespace(find_one=AsyncMock(return_value={"delivery_enqueued": False}), update_one=AsyncMock())
    monkeypatch.setattr(production.server, "db", SimpleNamespace(crm_outbox=outbox, leads=leads))
    monkeypatch.setattr(production, "_enabled_channels", lambda: ["max"])
    process = AsyncMock()
    monkeypatch.setattr(production, "_process_delivery", process)
    asyncio.run(production.durable_deliver_to_crm({"id": "test"}))
    outbox.update_one.assert_awaited_once()
    process.assert_not_called()


def test_consent_rejects_non_object_json():
    async def exercise():
        messages = []
        app = AsyncMock()
        middleware = production.RequireExplicitConsentMiddleware(app)
        receive = AsyncMock(return_value={"type": "http.request", "body": b"[]", "more_body": False})
        async def send(message):
            messages.append(message)
        await middleware({"type": "http", "method": "POST", "path": "/api/leads"}, receive, send)
        assert messages[0]["status"] == 400
        app.assert_not_called()
    asyncio.run(exercise())


def test_already_enqueued_lead_cannot_recreate_delivered_job(monkeypatch):
    outbox = SimpleNamespace(update_one=AsyncMock())
    leads = SimpleNamespace(find_one=AsyncMock(return_value={"delivery_enqueued": True}))
    monkeypatch.setattr(production.server, "db", SimpleNamespace(crm_outbox=outbox, leads=leads))
    asyncio.run(production.durable_deliver_to_crm({"id": "test"}))
    outbox.update_one.assert_not_called()


def test_smtp_failure_is_reported(monkeypatch):
    monkeypatch.setattr(email, "SMTP_HOST", "smtp.invalid")
    monkeypatch.setattr(email, "LEAD_EMAIL_TO", "test@example.com")
    def fail(*args, **kwargs):
        raise OSError("offline")
    monkeypatch.setattr(email.smtplib, "SMTP_SSL", fail)
    assert asyncio.run(email.send({"id": "test"})) is False


def test_max_failure_is_reported(monkeypatch):
    monkeypatch.setattr(max_int, "MAX_BOT_TOKEN", "test")
    monkeypatch.setattr(max_int, "MAX_ALERT_CHAT_ID", "test")
    monkeypatch.setattr(max_int, "send_message", AsyncMock(return_value=None))
    assert asyncio.run(max_int.send({"id": "test"})) is False


def test_notification_html_escapes_lead_values():
    lead = {"name": "<b>user</b>", "message": "<a href='https://example.com'>link</a>"}
    assert "<b>user</b>" not in telegram._format_message(lead)
    assert "&lt;b&gt;user&lt;/b&gt;" in email._build_html(lead)
