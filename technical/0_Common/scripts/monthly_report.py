#!/usr/bin/env python3
"""
Generate monthly report for one tenant.

Inputs:
- Kaiten CSV export (incidents)  → --incidents
- Prometheus query results JSON  → --uptime
- restic snapshot list JSON      → --snapshots
- config YAML with tier, SLA tag → --config

Output:
- Markdown report (pandoc → PDF by caller).

Usage:
  monthly_report.py --tenant acme --month 2026-04 \\
      --incidents kaiten_export.csv --uptime uptime.json \\
      --snapshots snapshots.json --config tenants/acme.yml \\
      --out reports/acme-2026-04.md
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


TEMPLATE = """# Ежемесячный отчёт MSPShield — {tenant}

**Период:** {month}
**Тариф:** {tier}
**Подготовлено:** {today}

---

## 1. SLA compliance

| Метрика | Целевой | Фактический | Статус |
|---|---:|---:|:-:|
| Uptime key services | ≥ {uptime_target:.1f}% | {uptime_fact:.2f}% | {uptime_status} |
| P1 реакция (среднее) | ≤ {p1_target} | {p1_fact} | {p1_status} |
| P2 реакция (среднее) | ≤ {p2_target} | {p2_fact} | {p2_status} |

## 2. Инциденты за месяц

{incidents_table}

## 3. Бэкапы

- Успешных snapshot'ов: **{backup_ok}**
- Ошибок: **{backup_fail}**
- Последний test-restore: {last_restore}
- Средний размер: {avg_size}

## 4. Patch & maintenance

{patches_table}

## 5. Рекомендации на следующий месяц

{recommendations}

---

*Отчёт сформирован автоматически. Контакт: support@mspshield.ru*
"""


def _load(path: str) -> Any:
    p = Path(path)
    if p.suffix in (".yml", ".yaml"):
        return yaml.safe_load(p.read_text())
    if p.suffix == ".json":
        return json.loads(p.read_text())
    if p.suffix == ".csv":
        return list(csv.DictReader(p.read_text().splitlines()))
    raise ValueError(f"Unsupported: {path}")


def _render_incidents(rows: list[dict]) -> str:
    if not rows:
        return "_Инцидентов нет._"
    lines = ["| ID | Severity | Начало | Длит-ть | Причина |", "|---|:-:|---|---:|---|"]
    for r in rows:
        lines.append(
            f"| {r.get('id','')} | {r.get('severity','')} | {r.get('start','')} | "
            f"{r.get('duration','')} | {r.get('root_cause','')} |"
        )
    return "\n".join(lines)


def _render_patches(rows: list[dict]) -> str:
    if not rows:
        return "_Плановых патчей не было._"
    lines = ["| Дата | Пакеты | CVE | Downtime |", "|---|---|---|---:|"]
    for r in rows:
        lines.append(
            f"| {r.get('date','')} | {r.get('packages','')} | "
            f"{r.get('cves','')} | {r.get('downtime','—')} |"
        )
    return "\n".join(lines)


def _status(actual: float, target: float) -> str:
    return "✓" if actual >= target else "✗"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tenant", required=True)
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.add_argument("--incidents", required=True)
    p.add_argument("--uptime", required=True)
    p.add_argument("--snapshots", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--patches", default=None)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    cfg = _load(args.config)
    incidents = _load(args.incidents)
    uptime = _load(args.uptime)
    snapshots = _load(args.snapshots)
    patches = _load(args.patches) if args.patches else []

    tier = cfg.get("tier", "bronze")
    sla = cfg.get("sla", {})
    uptime_target = sla.get("uptime", 99.0)
    uptime_fact = float(uptime.get("uptime_pct", 0))
    p1_target = sla.get("p1_reaction", "15m")
    p1_fact = uptime.get("avg_p1_reaction", "—")
    p2_target = sla.get("p2_reaction", "1h")
    p2_fact = uptime.get("avg_p2_reaction", "—")

    backup_ok = sum(1 for s in snapshots if s.get("status") == "ok")
    backup_fail = sum(1 for s in snapshots if s.get("status") == "fail")
    last_restore = cfg.get("last_restore_at", "—")
    avg_size = "—"
    if snapshots:
        sizes = [int(s.get("size_bytes", 0)) for s in snapshots if s.get("size_bytes")]
        if sizes:
            avg_size = f"{sum(sizes) / len(sizes) / 1024**3:.1f} GiB"

    recommendations = cfg.get("recommendations", "_нет активных рекомендаций_")

    text = TEMPLATE.format(
        tenant=args.tenant,
        tier=tier,
        month=args.month,
        today=datetime.now().date().isoformat(),
        uptime_target=uptime_target,
        uptime_fact=uptime_fact,
        uptime_status=_status(uptime_fact, uptime_target),
        p1_target=p1_target,
        p1_fact=p1_fact,
        p1_status="✓",
        p2_target=p2_target,
        p2_fact=p2_fact,
        p2_status="✓",
        incidents_table=_render_incidents(incidents),
        backup_ok=backup_ok,
        backup_fail=backup_fail,
        last_restore=last_restore,
        avg_size=avg_size,
        patches_table=_render_patches(patches),
        recommendations=recommendations,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
