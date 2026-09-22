"""Unit tests for the optional Kaiten integration; no network required."""
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from integrations import kaiten  # noqa: E402


def _configure(monkeypatch, lane=""):
    monkeypatch.setattr(kaiten, "KAITEN_DOMAIN", "msp-oblako.kaiten.ru")
    monkeypatch.setattr(kaiten, "KAITEN_API_TOKEN", "test-token")
    monkeypatch.setattr(kaiten, "KAITEN_BOARD_ID", "1234567")
    monkeypatch.setattr(kaiten, "KAITEN_COLUMN_ID", "999001")
    monkeypatch.setattr(kaiten, "KAITEN_LANE_ID", lane)


SAMPLE_LEAD = {
    "id": "4f3b0000-0000-0000-0000-000000000001",
    "name": "Иванов Иван",
    "company": "ООО Ромашка",
    "contact": "+7 999 1234567",
    "email": "ivan@romashka.ru",
    "servers": "4-10",
    "tariff": "silver",
    "source": "landing",
    "downtime_loss": 1200000,
    "message": "Нужен мониторинг и бэкапы",
}


def test_enabled_only_with_required_configuration(monkeypatch):
    _configure(monkeypatch)
    assert kaiten.is_enabled() is True
    monkeypatch.setattr(kaiten, "KAITEN_API_TOKEN", "")
    assert kaiten.is_enabled() is False


def test_lane_is_optional(monkeypatch):
    _configure(monkeypatch, lane="")
    assert kaiten.is_enabled() is True


def test_payload_contains_exact_external_id(monkeypatch):
    _configure(monkeypatch)
    payload = kaiten.build_card_payload(SAMPLE_LEAD)
    assert payload["title"] == "[silver] ООО Ромашка · Иванов Иван"
    assert payload["board_id"] == 1234567
    assert payload["column_id"] == 999001
    assert payload["external_id"] == SAMPLE_LEAD["id"]
    assert "lane_id" not in payload


def test_description_skips_empty_fields(monkeypatch):
    _configure(monkeypatch)
    lead = dict(SAMPLE_LEAD, email=None, message=None)
    description = kaiten._format_description(lead)
    assert "Email" not in description
    assert "Сообщение клиента" not in description
    assert SAMPLE_LEAD["id"] in description


def test_exact_card_selector_returns_match_not_first_card():
    cards = [
        {"id": 10, "external_id": "another-lead"},
        {"id": 42, "external_id": SAMPLE_LEAD["id"]},
    ]
    assert kaiten._select_exact_card(cards, SAMPLE_LEAD["id"])["id"] == 42


def test_exact_card_selector_returns_none_for_nonmatching_result_set():
    cards = [{"id": 10, "external_id": "another-lead"}]
    assert kaiten._select_exact_card(cards, SAMPLE_LEAD["id"]) is None


def test_create_card_returns_existing_without_post(monkeypatch):
    _configure(monkeypatch)
    existing = {"id": 42, "external_id": SAMPLE_LEAD["id"]}

    async def fake_find(external_id):
        assert external_id == SAMPLE_LEAD["id"]
        return existing

    monkeypatch.setattr(kaiten, "find_card_by_external_id", fake_find)
    assert asyncio.run(kaiten.create_card(SAMPLE_LEAD)) is existing


def test_create_card_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(kaiten, "KAITEN_API_TOKEN", "")
    assert asyncio.run(kaiten.create_card(SAMPLE_LEAD)) is None
