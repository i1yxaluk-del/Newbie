#!/usr/bin/env python3
"""Семидневный календарь фактически наблюдавшихся backup jobs из Prometheus.

VM, systemd timer каждые 5 минут; только чтение Prometheus и запись textfile.
Не читает restic/env/секреты. Отсутствие истории = -1, не успешный backup.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo


def query(base, expression, start, end):
    params = urlencode({"query": expression, "start": start, "end": end, "step": 300})
    with urlopen(base + "/api/v1/query_range?" + params, timeout=25) as response:
        result = json.load(response)
    if result.get("status") != "success":
        raise RuntimeError("Prometheus query failed")
    return result["data"]["result"]


def calendar(status_series, timestamp_series, now, tz):
    dates = [(now.astimezone(tz).date() - timedelta(days=i)).isoformat() for i in reversed(range(7))]
    timestamps = {}
    for series in timestamp_series:
        metric = series["metric"]
        key = (metric.get("host", metric.get("instance", "unknown")), metric.get("repo", "unknown"))
        timestamps[key] = {int(t): float(value) for t, value in series["values"]}
    rows = {}
    for series in status_series:
        metric = series["metric"]
        key = (metric.get("host", metric.get("instance", "unknown")), metric.get("repo", "unknown"))
        days = rows.setdefault(key, {day: (-1, -1, -1) for day in dates})
        for observed, raw in series["values"]:
            job = timestamps.get(key, {}).get(int(observed))
            if not job or job <= 0 or job > float(observed):
                continue
            day = datetime.fromtimestamp(job, tz).date().isoformat()
            state = float(raw)
            if day in days and state in (0, 1, 2) and (job, observed) >= days[day][:2]:
                days[day] = (job, observed, int(state))
    return rows


def render(rows, now):
    lines = ["# HELP msp_backup_day_status Observed job status: -1=no data, 0=failed, 1=success, 2=running",
             "# TYPE msp_backup_day_status gauge"]
    for (host, repo), days in sorted(rows.items()):
        for day, (_, _, state) in sorted(days.items()):
            labels = ",".join(f"{key}={json.dumps(value, ensure_ascii=True)}" for key, value in
                              [("host", host), ("repo", repo), ("date", day)])
            lines.append(f"msp_backup_day_status{{{labels}}} {state}")
    lines += ["# TYPE msp_backup_calendar_generated_seconds gauge", f"msp_backup_calendar_generated_seconds {now.timestamp()}"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
    parser.add_argument("--output", default="/var/lib/node_exporter/textfile_collector/backup_calendar.prom")
    parser.add_argument("--timezone", default="Europe/Moscow")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    # Одинаковая сетка обоих запросов позволяет сопоставить статус и timestamp.
    end = int(now.timestamp()) // 300 * 300
    start = end - 8 * 86400
    statuses = query(args.prometheus, "restic_backup_success", start, end)
    timestamps = query(args.prometheus, "restic_backup_timestamp_seconds", start, end)
    if not statuses:
        raise SystemExit("Нет backup-метрик; предыдущий export не заменён, проверяйте его возраст")
    data = render(calendar(statuses, timestamps, now, ZoneInfo(args.timezone)), now)
    output = Path(args.output)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(data, encoding="utf-8")
    temporary.chmod(0o644)
    temporary.replace(output)
    print("Backup calendar exported from observed Prometheus history")


if __name__ == "__main__":
    main()
