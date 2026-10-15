import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path

spec = importlib.util.spec_from_file_location("backup_calendar", Path(__file__).parents[1] / "backup_calendar.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_old_success_does_not_make_today_green():
    now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    old = int(datetime(2026, 10, 14, 1, tzinfo=timezone.utc).timestamp())
    observed = int(now.timestamp())
    statuses = [{"metric": {"host": "node", "repo": "backup"}, "values": [[observed, "1"]]}]
    timestamps = [{"metric": {"host": "node", "repo": "backup"}, "values": [[observed, str(old)]]}]
    days = module.calendar(statuses, timestamps, now, timezone(timedelta(hours=3)))[("node", "backup")]
    assert days["2026-10-14"][2] == 1
    assert days["2026-10-15"][2] == -1


def test_last_job_failure_wins_and_timezone_is_moscow():
    now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    job = int(datetime(2026, 10, 14, 22, tzinfo=timezone.utc).timestamp())
    metric = {"host": "node", "repo": "backup"}
    statuses = [{"metric": metric, "values": [[job + 300, "2"], [job + 600, "0"]]}]
    timestamps = [{"metric": metric, "values": [[job + 300, str(job)], [job + 600, str(job)]]}]
    rows = module.calendar(statuses, timestamps, now, timezone(timedelta(hours=3)))
    assert rows[("node", "backup")]["2026-10-15"][2] == 0
