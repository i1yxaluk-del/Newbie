"""Backend tests for MSPShield API — lead capture + admin endpoints."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Load from frontend .env as fallback
    from pathlib import Path
    env = Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")

ADMIN_TOKEN = "change-me-to-strong-random-string"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "X-Admin-Token": ADMIN_TOKEN})
    return s


# Health/root
class TestHealth:
    def test_health(self, api):
        r = api.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"

    def test_root(self, api):
        r = api.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["service"] == "MSPShield API"
        assert "version" in data


# Lead creation
class TestLeadCreate:
    def test_create_valid(self, api):
        payload = {
            "name": "TEST_Ivan",
            "company": "TEST_Acme LLC",
            "contact": "+7 999 1234567",
            "email": "test@example.com",
            "servers": "4-10",
            "tariff": "silver",
            "message": "TEST lead",
            "downtime_loss": "1 200 000 ₽/год",
        }
        r = api.post(f"{BASE_URL}/api/leads", json=payload, timeout=15)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data["id"], str) and len(data["id"]) > 10
        pytest.test_lead_id = data["id"]

    def test_minimal_valid(self, api):
        """Optional fields (email, tariff, message, downtime_loss) omitted."""
        payload = {
            "name": "TEST_Minimal",
            "company": "TEST_Co",
            "contact": "tg: @testuser",
            "servers": "1-3",
        }
        r = api.post(f"{BASE_URL}/api/leads", json=payload, timeout=15)
        assert r.status_code == 201, r.text
        assert r.json()["ok"] is True

    def test_invalid_servers(self, api):
        payload = {
            "name": "TEST_BadSrv",
            "company": "TEST_Co",
            "contact": "x@y.z",
            "servers": "500",
        }
        r = api.post(f"{BASE_URL}/api/leads", json=payload, timeout=15)
        assert r.status_code == 422

    def test_invalid_email(self, api):
        payload = {
            "name": "TEST_BadEmail",
            "company": "TEST_Co",
            "contact": "contact",
            "email": "not-an-email",
            "servers": "11-30",
        }
        r = api.post(f"{BASE_URL}/api/leads", json=payload, timeout=15)
        assert r.status_code == 422

    def test_missing_required(self, api):
        payload = {"name": "TEST_X"}  # missing company, contact, servers
        r = api.post(f"{BASE_URL}/api/leads", json=payload, timeout=15)
        assert r.status_code == 422


# Admin endpoints
class TestAdmin:
    def test_list_no_token(self, api):
        r = api.get(f"{BASE_URL}/api/leads", timeout=15)
        assert r.status_code == 401

    def test_list_wrong_token(self, api):
        r = api.get(f"{BASE_URL}/api/leads", headers={"X-Admin-Token": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_list_with_token(self, admin_api):
        r = admin_api.get(f"{BASE_URL}/api/leads", timeout=15)
        assert r.status_code == 200, r.text
        leads = r.json()
        assert isinstance(leads, list)
        assert len(leads) >= 1
        sample = leads[0]
        # No ObjectId leaking
        assert "_id" not in sample
        assert "id" in sample and "name" in sample and "servers" in sample and "status" in sample

    def test_stats(self, admin_api):
        r = admin_api.get(f"{BASE_URL}/api/stats", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "total_leads" in data
        assert "leads_today" in data
        assert "by_tariff" in data
        assert isinstance(data["by_tariff"], dict)
        assert data["total_leads"] >= 1

    def test_stats_unauthorized(self, api):
        r = api.get(f"{BASE_URL}/api/stats", timeout=15)
        assert r.status_code == 401

    def test_update_status_valid(self, admin_api):
        lead_id = getattr(pytest, "test_lead_id", None)
        assert lead_id, "need lead_id from previous test"
        r = admin_api.patch(
            f"{BASE_URL}/api/leads/{lead_id}/status",
            params={"new_status": "contacted"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        # verify persisted via list
        leads = admin_api.get(f"{BASE_URL}/api/leads", timeout=15).json()
        ours = next((x for x in leads if x["id"] == lead_id), None)
        assert ours is not None
        assert ours["status"] == "contacted"

    def test_update_status_invalid(self, admin_api):
        lead_id = getattr(pytest, "test_lead_id", None)
        assert lead_id
        r = admin_api.patch(
            f"{BASE_URL}/api/leads/{lead_id}/status",
            params={"new_status": "totally_fake"},
            timeout=15,
        )
        assert r.status_code == 400

    def test_update_status_not_found(self, admin_api):
        r = admin_api.patch(
            f"{BASE_URL}/api/leads/00000000-0000-0000-0000-000000000000/status",
            params={"new_status": "contacted"},
            timeout=15,
        )
        assert r.status_code == 404
