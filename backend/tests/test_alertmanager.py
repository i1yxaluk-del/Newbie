"""Unit-тесты для integrations/alertmanager.py — без сетевых вызовов."""
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Подставляем минимальные env до импорта server-модуля.
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "mspshield_test")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations import alertmanager, max as max_int, telegram  # noqa: E402


def _firing_alert(
    alertname: str = "HighCPU",
    severity: str = "warning",
    instance: str = "web-01",
    summary: str = "CPU > 90%",
    description: str = "CPU usage over threshold",
    runbook: str = "https://docs.example/runbooks/R-02",
) -> Dict[str, Any]:
    return {
        "status": "firing",
        "labels": {
            "alertname": alertname,
            "severity": severity,
            "instance": instance,
            "job": "node",
            "env": "prod",
        },
        "annotations": {
            "summary": summary,
            "description": description,
            "runbook": runbook,
        },
        "startsAt": "2026-05-06T03:47:12Z",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "http://prom/graph?expr=cpu",
    }


def _resolved_alert(**kw) -> Dict[str, Any]:
    a = _firing_alert(**kw)
    a["status"] = "resolved"
    a["endsAt"] = "2026-05-06T03:55:00Z"
    return a


def _payload(*alerts: Dict[str, Any], status: str = "firing") -> Dict[str, Any]:
    return {
        "version": "4",
        "groupKey": "{}/{}",
        "status": status,
        "receiver": "msp-max-tg",
        "groupLabels": {"alertname": "HighCPU"},
        "commonLabels": {"severity": "warning"},
        "commonAnnotations": {},
        "externalURL": "http://alertmanager",
        "alerts": list(alerts),
    }


class TestSeverityMap:
    def test_critical_to_p1(self):
        assert alertmanager.classify_severity("critical") == ("P1", "🔴")
        assert alertmanager.classify_severity("page") == ("P1", "🔴")
        assert alertmanager.classify_severity("error") == ("P1", "🔴")

    def test_warning_to_p2(self):
        assert alertmanager.classify_severity("warning")[0] == "P2"
        assert alertmanager.classify_severity("warn")[0] == "P2"

    def test_info_to_p3(self):
        assert alertmanager.classify_severity("info")[0] == "P3"
        assert alertmanager.classify_severity(None)[0] == "P3"
        assert alertmanager.classify_severity("")[0] == "P3"
        assert alertmanager.classify_severity("unknown")[0] == "P3"

    def test_case_insensitive(self):
        assert alertmanager.classify_severity("Critical")[0] == "P1"
        assert alertmanager.classify_severity("WARNING")[0] == "P2"


class TestVerifyToken:
    def test_empty_token_open(self, monkeypatch):
        monkeypatch.setattr(alertmanager, "ALERTMANAGER_WEBHOOK_TOKEN", "")
        assert alertmanager.verify_token(None) is True
        assert alertmanager.verify_token("anything") is True

    def test_token_required(self, monkeypatch):
        monkeypatch.setattr(alertmanager, "ALERTMANAGER_WEBHOOK_TOKEN", "s3cret")
        assert alertmanager.verify_token("Bearer s3cret") is True
        assert alertmanager.verify_token("bearer s3cret") is True
        assert alertmanager.verify_token("s3cret") is True
        assert alertmanager.verify_token("Bearer wrong") is False
        assert alertmanager.verify_token("") is False
        assert alertmanager.verify_token(None) is False


class TestParsePayload:
    def test_extracts_alerts(self):
        p = _payload(_firing_alert(), _firing_alert(alertname="HostDown"))
        out = alertmanager.parse_alertmanager_payload(p)
        assert len(out) == 2
        assert out[0]["labels"]["alertname"] == "HighCPU"
        assert out[1]["labels"]["alertname"] == "HostDown"

    def test_no_alerts_returns_empty(self):
        assert alertmanager.parse_alertmanager_payload({}) == []
        assert alertmanager.parse_alertmanager_payload({"alerts": None}) == []
        assert alertmanager.parse_alertmanager_payload({"alerts": "x"}) == []

    def test_skips_non_dict_alerts(self):
        out = alertmanager.parse_alertmanager_payload({"alerts": [_firing_alert(), "junk", None]})
        assert len(out) == 1


class TestFormatMarkdown:
    def test_firing_critical_has_p1(self):
        text = alertmanager.format_alert_markdown(_firing_alert(severity="critical"))
        assert "P1" in text
        assert "🔴" in text
        assert "HighCPU" in text  # alertname

    def test_firing_warning_has_p2(self):
        text = alertmanager.format_alert_markdown(_firing_alert(severity="warning"))
        assert "P2" in text
        assert "🟡" in text

    def test_resolved_has_check(self):
        text = alertmanager.format_alert_markdown(_resolved_alert(severity="critical"))
        assert "resolved" in text
        assert "✅" in text

    def test_includes_summary_and_meta(self):
        text = alertmanager.format_alert_markdown(_firing_alert())
        assert "CPU > 90%" in text
        assert "web-01" in text  # instance
        assert "prod" in text    # env

    def test_includes_runbook_link(self):
        text = alertmanager.format_alert_markdown(_firing_alert())
        assert "runbook" in text
        assert "https://docs.example" in text


class TestFormatHtml:
    def test_escapes_html(self):
        a = _firing_alert(summary="<script>alert(1)</script>", description="bad & ugly")
        text = alertmanager.format_alert_html(a)
        assert "<script>" not in text
        assert "&lt;script&gt;" in text
        assert "&amp;" in text

    def test_html_tags_for_telegram(self):
        text = alertmanager.format_alert_html(_firing_alert(severity="critical"))
        assert "<b>" in text  # bold tag
        assert "<code>" in text  # code tag for instance


class TestShouldDispatch:
    def test_firing_always_dispatched(self):
        assert alertmanager.should_dispatch(_firing_alert()) is True

    def test_resolved_respects_flag(self, monkeypatch):
        monkeypatch.setattr(alertmanager, "ALERT_RESOLVED_NOTIFY", False)
        assert alertmanager.should_dispatch(_resolved_alert()) is False
        monkeypatch.setattr(alertmanager, "ALERT_RESOLVED_NOTIFY", True)
        assert alertmanager.should_dispatch(_resolved_alert()) is True


class TestDispatchAlerts:
    def test_no_channels_skipped(self, monkeypatch):
        monkeypatch.setattr(alertmanager, "ALERT_CHANNELS", [])
        stats = asyncio.run(alertmanager.dispatch_alerts([_firing_alert()]))
        assert stats["skipped"] == 1

    def test_fan_out_max_and_telegram(self, monkeypatch):
        sent_max: List[str] = []
        sent_tg: List[str] = []

        async def fake_max(text, chat_id=None, fmt="markdown"):
            sent_max.append(text)
            return True

        async def fake_tg(text, chat_id=None, parse_mode="HTML"):
            sent_tg.append(text)
            return True

        monkeypatch.setattr(alertmanager, "ALERT_CHANNELS", ["max", "telegram"])
        monkeypatch.setattr(alertmanager, "_max_enabled", lambda: True)
        monkeypatch.setattr(alertmanager, "_telegram_enabled", lambda: True)
        monkeypatch.setattr(max_int, "send_alert_text", fake_max)
        monkeypatch.setattr(telegram, "send_alert_text", fake_tg)

        alerts = [_firing_alert(), _firing_alert(alertname="HostDown", severity="critical")]
        stats = asyncio.run(alertmanager.dispatch_alerts(alerts))
        assert stats["max_ok"] == 2
        assert stats["tg_ok"] == 2
        assert stats["max_err"] == 0
        assert stats["tg_err"] == 0
        # Markdown ушёл в MAX, HTML — в Telegram.
        assert any("**" in t for t in sent_max)
        assert any("<b>" in t for t in sent_tg)

    def test_skips_resolved_when_disabled(self, monkeypatch):
        async def fake_max(text, chat_id=None, fmt="markdown"):
            return True

        monkeypatch.setattr(alertmanager, "ALERT_CHANNELS", ["max"])
        monkeypatch.setattr(alertmanager, "_max_enabled", lambda: True)
        monkeypatch.setattr(alertmanager, "_telegram_enabled", lambda: False)
        monkeypatch.setattr(alertmanager, "ALERT_RESOLVED_NOTIFY", False)
        monkeypatch.setattr(max_int, "send_alert_text", fake_max)

        stats = asyncio.run(
            alertmanager.dispatch_alerts([_firing_alert(), _resolved_alert()])
        )
        assert stats["max_ok"] == 1
        assert stats["skipped"] == 1

    def test_counts_errors(self, monkeypatch):
        async def fake_max(text, chat_id=None, fmt="markdown"):
            return False  # симулируем ошибку отправки

        monkeypatch.setattr(alertmanager, "ALERT_CHANNELS", ["max"])
        monkeypatch.setattr(alertmanager, "_max_enabled", lambda: True)
        monkeypatch.setattr(alertmanager, "_telegram_enabled", lambda: False)
        monkeypatch.setattr(max_int, "send_alert_text", fake_max)

        stats = asyncio.run(alertmanager.dispatch_alerts([_firing_alert()]))
        assert stats["max_ok"] == 0
        assert stats["max_err"] == 1
