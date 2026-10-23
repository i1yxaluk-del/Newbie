#!/usr/bin/env python3
"""Применить учебный комплект только в существующем lab Wazuh 4.14.5.

VM: sudo python3 /home/service/wazuh-lab/business/apply.py
Сохраняет конфигурацию/правило и экспорт прежних объектов dashboard до замены.
Меняет два учебных источника, добавляет правила, перезапускает только manager.
Не создаёт клиентские агенты, не включает блокировки и не пишет alerts напрямую.
"""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dashboards import objects

ROOT = Path("/home/service/wazuh-lab")
MANAGER = "msp-wazuh-lab-wazuh.manager-1"


def dashboard_request(path, payload, headers):
    """API только локальной лаборатории; self-signed исключение не переносить клиенту."""
    request = Request("https://192.168.114.10" + path, data=json.dumps(payload).encode(),
                      headers=headers, method="POST")
    with urlopen(request, context=ssl._create_unverified_context(), timeout=45) as response:
        return response.read()


def main():
    if os.geteuid() != 0:
        raise SystemExit("Требуется sudo на учебной VM")
    os.umask(0o077)
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if manifest.get("version") != "4.14.5" or manifest.get("purpose") != "training-only":
        raise SystemExit("Неизвестная версия/назначение стенда")
    project = Path(manifest["project"])
    config = project / "config/wazuh_cluster/wazuh_manager.conf"
    backup = ROOT / "business-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(config, backup / "wazuh_manager.conf")
    effective = subprocess.check_output(["docker", "exec", MANAGER, "cat", "/var/ossec/etc/ossec.conf"])
    (backup / "effective-ossec.conf").write_bytes(effective)
    # Два разных log_format: JSON для наших контрактов, syslog для штатного sshd decoder.
    text = config.read_text()
    for filename, fmt in [("business.jsonl", "json"), ("business-native.log", "syslog")]:
        path = ROOT / "training" / filename
        path.touch(exist_ok=True)
        path.chmod(0o644)
        location = "/var/ossec/lab/" + filename
        if location not in text:
            text += f"\n<ossec_config><localfile><log_format>{fmt}</log_format><location>{location}</location></localfile></ossec_config>\n"
    config.write_text(text)
    target = "/var/ossec/etc/rules/msp_business_rules.xml"
    previous = subprocess.run(["docker", "exec", MANAGER, "cat", target], capture_output=True)
    if previous.returncode == 0:
        (backup / "msp_business_rules.xml").write_bytes(previous.stdout)
    subprocess.run(["docker", "cp", str(Path(__file__).parent / "rules.xml"), MANAGER + ":" + target], check=True)
    subprocess.run(["docker", "exec", MANAGER, "chown", "wazuh:wazuh", target], check=True)
    subprocess.run(["docker", "exec", MANAGER, "chmod", "640", target], check=True)
    subprocess.run(["docker", "cp", str(config), MANAGER + ":/var/ossec/etc/ossec.conf"], check=True)
    validation = subprocess.run(["docker", "exec", MANAGER, "/var/ossec/bin/wazuh-analysisd", "-t"], capture_output=True)
    if validation.returncode:
        shutil.copy2(backup / "wazuh_manager.conf", config)
        subprocess.run(["docker", "cp", str(backup / "effective-ossec.conf"), MANAGER + ":/var/ossec/etc/ossec.conf"], check=True)
        if (backup / "msp_business_rules.xml").exists():
            subprocess.run(["docker", "cp", str(backup / "msp_business_rules.xml"), MANAGER + ":" + target], check=True)
        else:
            subprocess.run(["docker", "exec", MANAGER, "rm", target], check=True)
        raise SystemExit("Ошибка проверки правил; исходные файлы возвращены, перезапуска нет")
    # Образ копирует /wazuh-config-mount в persistent etc при инициализации.
    # Явно обновить effective ossec.conf, иначе новый localfile останется лишь в шаблоне.
    subprocess.run(["docker", "cp", str(config), MANAGER + ":/var/ossec/etc/ossec.conf"], check=True)
    subprocess.run(["docker", "exec", MANAGER, "chown", "root:wazuh", "/var/ossec/etc/ossec.conf"], check=True)
    subprocess.run(["docker", "exec", MANAGER, "chmod", "640", "/var/ossec/etc/ossec.conf"], check=True)
    subprocess.run(["docker", "restart", MANAGER], check=True)
    credentials = json.loads((ROOT / "credentials.json").read_text())
    headers = {"Authorization": "Basic " + base64.b64encode(("admin:" + credentials["admin"]).encode()).decode(),
               "osd-xsrf": "true", "Content-Type": "application/json"}
    collection = objects()
    # Экспорт только известных ID перед overwrite, не все пользовательские данные.
    existing = []
    for item in collection:
        lookup = Request("https://192.168.114.10/api/saved_objects/" + item["type"] + "/" + item["id"], headers=headers)
        try:
            with urlopen(lookup, context=ssl._create_unverified_context(), timeout=20):
                existing.append({"type": item["type"], "id": item["id"]})
        except HTTPError as exc:
            if exc.code != 404:
                raise
    export = dashboard_request("/api/saved_objects/_export", {"objects": existing, "includeReferencesDeep": False}, headers) if existing else b""
    (backup / "saved-objects-before.ndjson").write_bytes(export)
    # bulk_create сохраняет существующие saved objects API, не лезет в системный индекс.
    request = Request("https://192.168.114.10/api/saved_objects/_bulk_create?overwrite=true",
                      data=json.dumps(collection).encode(), headers=headers, method="POST")
    with urlopen(request, context=ssl._create_unverified_context(), timeout=45) as response:
        result = json.load(response)
    errors = [item.get("id") for item in result.get("saved_objects", []) if item.get("error")]
    if errors:
        raise SystemExit("Не все объекты приняты: " + ",".join(errors))
    (ROOT / "business-objects.json").write_text(json.dumps(collection, ensure_ascii=False, indent=2))
    print("Комплект применён; объектов:", len(result.get("saved_objects", [])), "; backup:", backup)
    for item in collection:
        if item["type"] == "dashboard":
            print("/app/dashboards#/view/" + item["id"], item["attributes"]["title"])


if __name__ == "__main__":
    main()
