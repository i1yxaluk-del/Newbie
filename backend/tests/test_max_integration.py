"""Unit-тесты для integrations/max.py — без сетевых вызовов."""
import os
import sys
from pathlib import Path

# Подставляем минимальные env до импорта server-модуля.
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "mspshield_test")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations import max as max_int  # noqa: E402


class TestExtractChatAndText:
    def test_empty_update(self):
        result = max_int.extract_chat_and_text({})
        assert result["update_type"] is None
        assert result["chat_id"] is None
        assert result["user_id"] is None
        assert result["text"] is None

    def test_message_created(self):
        upd = {
            "update_type": "message_created",
            "timestamp": 1_710_412_800,
            "message": {
                "recipient": {"chat_id": 42},
                "sender": {"user_id": 5, "name": "Anton"},
                "body": {"mid": "msg_001", "text": "Хочу узнать статус заказа"},
            },
        }
        result = max_int.extract_chat_and_text(upd)
        assert result["update_type"] == "message_created"
        assert result["chat_id"] == 42
        assert result["user_id"] == 5
        assert result["user_name"] == "Anton"
        assert result["text"] == "Хочу узнать статус заказа"
        assert result["mid"] == "msg_001"

    def test_bot_started(self):
        upd = {
            "update_type": "bot_started",
            "chat_id": 9,
            "user": {"user_id": 9, "name": "TestUser"},
        }
        result = max_int.extract_chat_and_text(upd)
        assert result["update_type"] == "bot_started"
        assert result["chat_id"] == 9
        assert result["user_id"] == 9
        assert result["user_name"] == "TestUser"

    def test_message_callback(self):
        upd = {
            "update_type": "message_callback",
            "callback": {
                "callback_id": "cb1",
                "payload": "tariff_silver",
                "user": {"user_id": 7, "name": "Maria"},
            },
            "message": {"recipient": {"chat_id": 33}},
        }
        result = max_int.extract_chat_and_text(upd)
        assert result["update_type"] == "message_callback"
        assert result["chat_id"] == 33
        assert result["user_id"] == 7
        assert result["payload"] == "tariff_silver"


class TestIsEnabled:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.setattr(max_int, "MAX_BOT_TOKEN", "")
        assert max_int.is_enabled() is False
        assert max_int.is_alert_channel() is False

    def test_enabled_with_token(self, monkeypatch):
        monkeypatch.setattr(max_int, "MAX_BOT_TOKEN", "mb-test")
        monkeypatch.setattr(max_int, "MAX_ALERT_CHAT_ID", "")
        assert max_int.is_enabled() is True
        assert max_int.is_alert_channel() is False

    def test_alert_channel_with_chat(self, monkeypatch):
        monkeypatch.setattr(max_int, "MAX_BOT_TOKEN", "mb-test")
        monkeypatch.setattr(max_int, "MAX_ALERT_CHAT_ID", "42")
        assert max_int.is_alert_channel() is True


class TestVerifyWebhookSecret:
    def test_empty_secret_accepts_anything(self, monkeypatch):
        monkeypatch.setattr(max_int, "MAX_WEBHOOK_SECRET", "")
        assert max_int.verify_webhook_secret("foo") is True
        assert max_int.verify_webhook_secret(None) is True

    def test_secret_required(self, monkeypatch):
        monkeypatch.setattr(max_int, "MAX_WEBHOOK_SECRET", "secret-value")
        assert max_int.verify_webhook_secret("secret-value") is True
        assert max_int.verify_webhook_secret("wrong") is False
        assert max_int.verify_webhook_secret(None) is False


class TestDeeplink:
    def test_deeplink_with_username(self, monkeypatch):
        monkeypatch.setattr(max_int, "MAX_BOT_USERNAME", "msp_oblako_bot")
        assert max_int.bot_deeplink() == "https://max.ru/msp_oblako_bot"

    def test_deeplink_without_username(self, monkeypatch):
        monkeypatch.setattr(max_int, "MAX_BOT_USERNAME", "")
        assert max_int.bot_deeplink() is None


class TestButtons:
    def test_welcome_buttons_shape(self):
        buttons = max_int.welcome_buttons()
        assert isinstance(buttons, list)
        # хотя бы 3 ряда: calc, tariffs, contact
        assert len(buttons) >= 3
        for row in buttons:
            assert isinstance(row, list)
            for btn in row:
                assert "type" in btn
                assert "text" in btn

    def test_tariffs_buttons_have_back(self):
        buttons = max_int.tariffs_buttons()
        flat = [b for row in buttons for b in row]
        payloads = [b.get("payload") for b in flat]
        assert "tariff_bronze" in payloads
        assert "tariff_silver" in payloads
        assert "tariff_gold" in payloads
        assert "back_to_welcome" in payloads
