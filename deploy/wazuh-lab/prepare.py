#!/usr/bin/env python3
"""Учебный Wazuh: готовит отдельный upstream Docker-проект, без запуска.

VM: sudo python3 prepare.py --host-ip 192.168.114.10
Нужны git, Docker, standalone docker-compose, python3-yaml, python3-bcrypt.
Секреты — только root-readable local files; stdout их не содержит.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import xml.etree.ElementTree as ET

import bcrypt
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-ip", required=True)
    parser.add_argument("--root", default="/home/service/wazuh-lab")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Требуется sudo")
    os.umask(0o077)
    root = Path(args.root)
    if root.exists():
        raise SystemExit("Каталог уже существует: не перезаписываем учебные данные")
    if shutil.disk_usage("/home").free < 50 * 1024**3 or shutil.disk_usage("/var/lib/docker").free < 10 * 1024**3:
        raise SystemExit("Нужно ≥50 GiB на /home и ≥10 GiB для Docker images")
    root.mkdir(mode=0o700)
    upstream = root / "upstream"
    subprocess.run(["git", "clone", "--depth", "1", "--branch", "v4.14.5", "https://github.com/wazuh/wazuh-docker.git", str(upstream)], check=True)
    project = upstream / "single-node"
    config = yaml.safe_load((project / "docker-compose.yml").read_text())
    passwords = {key: "LabA1!" + secrets.token_urlsafe(24) for key in ["admin", "kibanaserver", "api"]}
    # Только нужные пользователи indexer, без известных demo passwords.
    users = {"_meta": {"type": "internalusers", "config_version": 2}}
    for user in ["admin", "kibanaserver"]:
        users[user] = {"hash": bcrypt.hashpw(passwords[user].encode(), bcrypt.gensalt()).decode(), "reserved": True}
    users["admin"]["backend_roles"] = ["admin"]
    (project / "config/wazuh_indexer/internal_users.yml").write_text(yaml.safe_dump(users))
    dashboard_wazuh = project / "config/wazuh_dashboard/wazuh.yml"
    dashboard_wazuh.write_text(yaml.safe_dump({"hosts": [{1513629884013: {"url": "https://wazuh.manager", "port": 55000, "username": "wazuh-wui", "password": passwords["api"], "run_as": True}}]}))
    data = root / "data"
    data.mkdir()
    for name in list(config["volumes"]):
        path = data / name
        path.mkdir()
        # UID контейнеров определяется Docker entrypoint; named volumes остаются,
        # но их local-driver bind хранит state на просторном /home.
        path.chmod(0o755)
        config["volumes"][name] = {"driver": "local", "driver_opts": {"type": "none", "o": "bind", "device": str(path)}}
    for name, service in config["services"].items():
        service["restart"] = "unless-stopped"
        environment = service.get("environment", [])
        values = dict(item.split("=", 1) for item in environment)
        for key in ["INDEXER_PASSWORD", "DASHBOARD_PASSWORD", "API_PASSWORD"]:
            if key in values:
                values[key] = passwords[{"INDEXER_PASSWORD": "admin", "DASHBOARD_PASSWORD": "kibanaserver", "API_PASSWORD": "api"}[key]]
        service["environment"] = values
        service["logging"] = {"driver": "json-file", "options": {"max-size": "10m", "max-file": "3"}}
        service["cpus"] = 4
        service["mem_limit"] = {"wazuh.manager": "3g", "wazuh.indexer": "4g", "wazuh.dashboard": "2g"}[name]
    config["services"]["wazuh.manager"]["ports"] = [f"{args.host_ip}:1514:1514", "127.0.0.1:55000:55000"]
    config["services"]["wazuh.indexer"]["ports"] = ["127.0.0.1:9200:9200"]
    config["services"]["wazuh.dashboard"]["ports"] = [f"{args.host_ip}:443:5601"]
    # Ограничить FIM учебным каталогом; host paths/socket внутрь manager не передаются.
    manager_path = project / "config/wazuh_cluster/wazuh_manager.conf"
    tree = ET.fromstring("<root>" + manager_path.read_text() + "</root>")
    main_config = tree.find("ossec_config")
    for auth in main_config.findall("auth"):
        auth.find("disabled").text = "yes"  # enrollment порт не открыт
    syscheck = main_config.find("syscheck")
    for directory in list(syscheck.findall("directories")):
        syscheck.remove(directory)
    ET.SubElement(syscheck, "directories", {"realtime": "yes", "check_all": "yes"}).text = "/var/ossec/lab/fim"
    lab_dir = root / "training"
    lab_dir.mkdir()
    (lab_dir / "fim").mkdir()
    (lab_dir / "events.jsonl").touch()
    lab_dir.chmod(0o755)
    (lab_dir / "fim").chmod(0o755)
    (lab_dir / "events.jsonl").chmod(0o644)
    localfile = ET.SubElement(main_config, "localfile")
    ET.SubElement(localfile, "log_format").text = "json"
    ET.SubElement(localfile, "location").text = "/var/ossec/lab/events.jsonl"
    manager_path.write_text("\n".join(ET.tostring(child, encoding="unicode") for child in tree))
    config["services"]["wazuh.manager"]["volumes"].append(f"{lab_dir}:/var/ossec/lab:ro")
    (project / "docker-compose.yml").write_text(yaml.safe_dump(config, sort_keys=False))
    # Non-root indexer/dashboard должны читать bind configs; родитель lab остаётся 0700.
    for relative in ["config/wazuh_indexer/wazuh.indexer.yml", "config/wazuh_indexer/internal_users.yml", "config/wazuh_dashboard/opensearch_dashboards.yml", "config/wazuh_dashboard/wazuh.yml"]:
        path = project / relative
        os.chown(path, 1000, 1000)
        path.chmod(0o600)
    credentials = root / "credentials.json"
    credentials.write_text(json.dumps({"dashboard_url": f"https://{args.host_ip}", "username": "admin", **passwords}, indent=2))
    credentials.chmod(0o600)
    (root / "manifest.json").write_text(json.dumps({"version": "4.14.5", "upstream_commit": subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip(), "host_ip": args.host_ip, "project": str(project), "purpose": "training-only"}, indent=2))
    print("Prepared", project, "; credentials stored root-only; default passwords replaced")


if __name__ == "__main__":
    main()
