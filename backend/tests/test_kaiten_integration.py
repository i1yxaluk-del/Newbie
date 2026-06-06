"""Юнит-тесты интеграции Kaiten (backend/integrations/kaiten.py).

Не требуют запущенного сервера и сети — проверяют чистую логику:
сборку payload, форматирование описания, флаг is_enabled и идемпотентность
create_card (с замоканным поиском существующей карточки).

Запуск:
    cd backend && python -m pytest tests/test_kaiten_integration.py -v
"""
import asyncio
import sys
from pathlib import Path

# Делаем пакет integrations импортируемым из каталога backend/.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from integrations import kaiten  # noqa: E402


def _configure(monkeypatch, lane=""):
    """Выставляем валидный конфиг модуля для тестов."""
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
    "servers": "5-10",
    "tariff": "silver",
    "source": "landing",
    "downtime_loss": 1200000,
    "message": "Нужен мониторинг и бэкапы",
}


class TestIsEnabled:
    def test_enabled_when_all_set(self, monkeypatch):
        _configure(monkeypatch)
        assert kaiten.is_enabled() is True

    def test_disabled_when_token_missing(self, monkeypatch):
        _configure(monkeypatch)
        monkeypatch.setattr(kaiten, "KAITEN_API_TOKEN", "")
        assert kaiten.is_enabled() is False

    def test_lane_is_optional(self, monkeypatch):
        _configure(monkeypatch, lane="")
        assert kaiten.is_enabled() is True


class TestBuildPayload:
    def test_title_and_ids(self, monkeypatch):
        _configure(monkeypatch)
        p = kaiten.build_card_payload(SAMPLE_LEAD)
        assert p["title"] == "[silver] ООО Ромашка · Иванов Иван"
        assert p["board_id"] == 1234567  # приведено к int
        assert p["column_id"] == 999001
        assert p["external_id"] == SAMPLE_LEAD["id"]
        assert "lane_id" not in p  # дорожка не задана

    def test_lane_added_when_set(self, monkeypatch):
        _configure(monkeypatch, lane="555")
        p = kaiten.build_card_payload(SAMPLE_LEAD)
        assert p["lane_id"] == 555

    def test_description_skips_empty_and_has_lead_id(self, monkeypatch):
        _configure(monkeypatch)
        lead = dict(SAMPLE_LEAD, email=None, message=None)
        desc = kaiten._format_description(lead)
        assert "Email" not in desc          # пустое поле пропущено
        assert "Сообщение клиента" not in desc
        assert SAMPLE_LEAD["id"] in desc    # lead_id всегда в описании
        assert "**Компания:** ООО Ромашка" in desc


class TestCreateCardIdempotency:
    def test_noop_when_disabled(self, monkeypatch):
        monkeypatch.setattr(kaiten, "KAITEN_API_TOKEN", "")
        result = asyncio.run(kaiten.create_card(SAMPLE_LEAD))
        assert result is None

    def test_returns_existing_without_creating(self, monkeypatch):
        _configure(monkeypatch)
        existing = {"id": 42, "external_id": SAMPLE_LEAD["id"]}

        async def fake_find(external_id):
            return existing

        # Если бы create_card попытался создать карточку, он бы пошёл в сеть
        # и упал — но idempotency должна вернуть existing раньше.
        monkeypatch.setattr(kaiten, "find_card_by_external_id", fake_find)
        result = asyncio.run(kaiten.create_card(SAMPLE_LEAD))
        assert result is existing
