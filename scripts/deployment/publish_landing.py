#!/usr/bin/env python3
"""Публикация готовой CRA-сборки на VM, без изменения backend/env/Caddy.

Запуск на VM: sudo python3 publish_landing.py /tmp/landing-release.tar.gz
Backup и manifest: /var/www/releases/<UTC>; rollback описан в stdout без секретов.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
from datetime import datetime, timezone


def publish(archive):
    if os.geteuid() != 0:
        raise SystemExit("Требуется sudo")
    live = Path("/var/www/landing")
    if not live.is_dir() or live.is_symlink():
        raise SystemExit("Ожидался существующий каталог /var/www/landing")
    release = Path("/var/www/releases") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    release.mkdir(parents=True, exist_ok=False)
    candidate = release / "candidate"
    candidate.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            target = (candidate / member.name).resolve()
            if not target.is_relative_to(candidate.resolve()) or not (member.isdir() or member.isfile()):
                raise SystemExit("Небезопасный путь/тип в release archive")
        tar.extractall(candidate, members=members)
    index = candidate / "index.html"
    assets = list((candidate / "static/js").glob("main.*.js"))
    if not index.is_file() or not assets:
        raise SystemExit("Нет CRA index/main bundle")
    for path in candidate.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)
    candidate.chmod(0o755)
    # Сохраняем старые hashed assets: уже открытые вкладки могут запросить lazy chunk.
    if (live / "static").exists():
        shutil.copytree(live / "static", candidate / "static", dirs_exist_ok=True)
    backup = release / "previous"
    os.rename(live, backup)
    try:
        os.rename(candidate, live)
    except BaseException:
        os.rename(backup, live)
        raise
    manifest = {"published_at": datetime.now(timezone.utc).isoformat(),
                "archive_sha256": hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
                "main_bundle": assets[0].name, "previous": str(backup)}
    (release / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(f"Rollback: sudo mv /var/www/landing {release}/rejected && sudo mv {backup} /var/www/landing")


if __name__ == "__main__":
    publish(sys.argv[1])
