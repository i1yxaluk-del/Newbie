"""
Alertmanager webhook receiver — fan-out в MAX и Telegram.

Prometheus Alertmanager отправляет POST с payload вида (v4):

    {
      "version": "4",
      "groupKey": "{}/{...}:{alertname=\"...\"}",
      "status": "firing" | "resolved",
      "receiver": "msp-max-tg",
      "groupLabels": {...},
      "commonLabels": {...},
      "commonAnnotations": {...},
      "externalURL": "https://alertmanager...",
      "alerts": [
        {
          "status": "firing" | "resolved",
          "labels":      {"alertname": "...", "severity": "critical", ...},
          "annotations": {"summary": "...", "description": "...", "runbook": "..."},
          "startsAt":    "2026-05-06T03:47:12Z",
          "endsAt":      "0001-01-01T00:00:00Z",
          "generatorURL":"http://prometheus.../graph?..."
        }, ...
      ]
    }

Severity-mapping → P1/P2/P3:
  critical                   → P1
  page / high                → P1
  warning                    → P2
  info / none / <empty>      → P3

Конфиг через env:

- ALERTMANAGER_WEBHOOK_TOKEN — Bearer-токен, который Alertmanager присылает в
  заголовке `Authorization: Bearer <token>`. Если пуст — приёмник
  открыт (НЕ рекомендуется для прода).
- ALERT_CHANNELS              — список каналов через запятую: "max,telegram".
                                По умолчанию — оба, если настроены.
- ALERT_RESOLVED_NOTIFY       — "true"/"false". Отправлять ли уведомления
                                о resolved-алертах. По умолчанию true.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from integrations import max as max_integration, telegram

logger = logging.getLogger("mspshield.alertmanager")

ALERTMANAGER_WEBHOOK_TOKEN = os.environ.get("ALERTMANAGER_WEBHOOK_TOKEN", "").strip()
_RAW_CHANNELS = os.environ.get("ALERT_CHANNELS", "max,telegram").strip()
ALERT_CHANNELS = [c.strip().lower() for c in _RAW_CHANNELS.split(",") if c.strip()]
ALERT_RESOLVED_NOTIFY = os.environ.get("ALERT_RESOLVED_NOTIFY", "true").lower() == "true"

# Severity → (priority, emoji)
_SEVERITY_MAP: Dict[str, Tuple[str, str]] = {
    "critical": ("P1", "🔴"),
    "page": ("P1", "🔴"),
    "high": ("P1", "🔴"),
    "error": ("P1", "🔴"),
    "warning": ("P2", "🟡"),
    "warn": ("P2", "🟡"),
    "info": ("P3", "🔵"),
    "notice": ("P3", "🔵"),
}
_RESOLVED_EMOJI = "✅"


def is_enabled() -> bool:
    """Хотя бы один канал реально может отправить сообщение."""
    return _max_enabled() or _telegram_enabled()


def _max_enabled() -> bool:
    return "max" in ALERT_CHANNELS and max_integration.is_alert_channel()


def _telegram_enabled() -> bool:
    return "telegram" in ALERT_CHANNELS and telegram.is_alert_channel()


def verify_token(received: Optional[str]) -> bool:
    """
    Сверяет заголовок Authorization с `ALERTMANAGER_WEBHOOK_TOKEN`.
    Принимаем как `Bearer <token>`, так и просто `<token>`.
    Если токен в env не задан — приёмник открыт (валидно всегда).
    """
    if not ALERTMANAGER_WEBHOOK_TOKEN:
        return True
    if not received:
        return False
    raw = received.strip()
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    return raw == ALERTMANAGER_WEBHOOK_TOKEN


def classify_severity(severity: Optional[str]) -> Tuple[str, str]:
    """Возвращает (P1/P2/P3, emoji)."""
    key = (severity or "").lower().strip()
    return _SEVERITY_MAP.get(key, ("P3", "🔵"))


def _human_time(iso: Optional[str]) -> str:
    """ISO-time → 'HH:MM:SS UTC' для краткости. Если не парсится — возвращаем как есть."""
    if not iso:
        return "—"
    try:
        # Alertmanager шлёт RFC3339 с 'Z' или offset.
        s = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:  # noqa: BLE001
        return iso


def format_alert_markdown(alert: Dict[str, Any]) -> str:
    """
    Markdown-формат для MAX. MAX поддерживает **bold**, *italic*, `code`.
    """
    status = (alert.get("status") or "").lower()
    labels = alert.get("labels") or {}
    annotations = alert.get("annotations") or {}

    severity = labels.get("severity")
    priority, emoji = classify_severity(severity)
    if status == "resolved":
        emoji = _RESOLVED_EMOJI
        head = f"{emoji} **resolved · {priority}**"
    else:
        head = f"{emoji} **{priority} · alert**"

    alertname = labels.get("alertname") or "alert"
    summary = annotations.get("summary") or annotations.get("description") or ""
    description = annotations.get("description") if annotations.get("summary") else ""
    instance = labels.get("instance") or labels.get("host") or labels.get("service")
    job = labels.get("job")
    env = labels.get("env") or labels.get("environment")
    runbook = annotations.get("runbook") or annotations.get("runbook_url")
    generator = alert.get("generatorURL")

    when = _human_time(
        alert.get("endsAt") if status == "resolved" else alert.get("startsAt")
    )

    lines: List[str] = [head, f"**{alertname}**"]
    if summary:
        lines.append(summary)
    if description and description != summary:
        lines.append(description)

    meta: List[str] = []
    if instance:
        meta.append(f"instance: `{instance}`")
    if job:
        meta.append(f"job: `{job}`")
    if env:
        meta.append(f"env: `{env}`")
    if severity:
        meta.append(f"severity: `{severity}`")
    meta.append(f"time: `{when}`")
    if meta:
        lines.append("\n".join(meta))

    links: List[str] = []
    if runbook:
        links.append(f"[runbook]({runbook})")
    if generator:
        links.append(f"[graph]({generator})")
    if links:
        lines.append(" · ".join(links))

    return "\n\n".join(lines)


def format_alert_html(alert: Dict[str, Any]) -> str:
    """HTML-формат для Telegram (parse_mode=HTML)."""
    status = (alert.get("status") or "").lower()
    labels = alert.get("labels") or {}
    annotations = alert.get("annotations") or {}

    severity = labels.get("severity")
    priority, emoji = classify_severity(severity)
    if status == "resolved":
        emoji = _RESOLVED_EMOJI
        head = f"{emoji} <b>resolved · {priority}</b>"
    else:
        head = f"{emoji} <b>{priority} · alert</b>"

    alertname = _esc(labels.get("alertname") or "alert")
    summary = _esc(annotations.get("summary") or annotations.get("description") or "")
    description = ""
    if annotations.get("summary") and annotations.get("description"):
        description = _esc(annotations.get("description"))
    instance = labels.get("instance") or labels.get("host") or labels.get("service")
    job = labels.get("job")
    env = labels.get("env") or labels.get("environment")
    runbook = annotations.get("runbook") or annotations.get("runbook_url")
    generator = alert.get("generatorURL")

    when = _esc(
        _human_time(alert.get("endsAt") if status == "resolved" else alert.get("startsAt"))
    )

    lines: List[str] = [head, f"<b>{alertname}</b>"]
    if summary:
        lines.append(summary)
    if description:
        lines.append(description)

    meta: List[str] = []
    if instance:
        meta.append(f"instance: <code>{_esc(instance)}</code>")
    if job:
        meta.append(f"job: <code>{_esc(job)}</code>")
    if env:
        meta.append(f"env: <code>{_esc(env)}</code>")
    if severity:
        meta.append(f"severity: <code>{_esc(severity)}</code>")
    meta.append(f"time: <code>{when}</code>")
    lines.append("\n".join(meta))

    links: List[str] = []
    if runbook:
        links.append(f'<a href="{_esc(runbook)}">runbook</a>')
    if generator:
        links.append(f'<a href="{_esc(generator)}">graph</a>')
    if links:
        lines.append(" · ".join(links))

    return "\n\n".join(lines)


def _esc(s: Optional[str]) -> str:
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def parse_alertmanager_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Извлекает список алертов из payload-а Alertmanager.
    Возвращает плоский list dicts с полями status/labels/annotations/startsAt/endsAt/generatorURL.
    """
    alerts = payload.get("alerts")
    if not isinstance(alerts, list):
        return []
    out: List[Dict[str, Any]] = []
    for a in alerts:
        if not isinstance(a, dict):
            continue
        out.append(a)
    return out


def should_dispatch(alert: Dict[str, Any]) -> bool:
    """Фильтр: пропускать ли алерт. resolved — по флагу ALERT_RESOLVED_NOTIFY."""
    status = (alert.get("status") or "").lower()
    if status == "resolved" and not ALERT_RESOLVED_NOTIFY:
        return False
    return True


async def dispatch_alerts(alerts: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Отправить алерты во все настроенные каналы.
    Возвращает счётчик `{channel: ok_count}` для метрик.
    """
    stats: Dict[str, int] = {"max_ok": 0, "max_err": 0, "tg_ok": 0, "tg_err": 0, "skipped": 0}

    if not alerts:
        return stats

    use_max = _max_enabled()
    use_tg = _telegram_enabled()
    if not (use_max or use_tg):
        logger.warning("alertmanager: no channels enabled, skipping %d alerts", len(alerts))
        stats["skipped"] = len(alerts)
        return stats

    for alert in alerts:
        if not should_dispatch(alert):
            stats["skipped"] += 1
            continue

        if use_max:
            text_md = format_alert_markdown(alert)
            try:
                ok = await max_integration.send_alert_text(text_md, fmt="markdown")
                stats["max_ok" if ok else "max_err"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("alertmanager → max failed: %s", exc)
                stats["max_err"] += 1

        if use_tg:
            text_html = format_alert_html(alert)
            try:
                ok = await telegram.send_alert_text(text_html, parse_mode="HTML")
                stats["tg_ok" if ok else "tg_err"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("alertmanager → telegram failed: %s", exc)
                stats["tg_err"] += 1

    return stats
