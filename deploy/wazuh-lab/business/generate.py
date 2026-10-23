#!/usr/bin/env python3
"""VM: добавить небольшой набор помеченных событий и контрольные журналы SSH.

Никаких сетевых входов/атак: только запись в выделенные файлы учебного источника.
Пишет manifest конкретного запуска для последующей проверки rule.id в индексе.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid


def make_event(scenario, run_id):
    """Стабильная схема строковых условий; synthetic явно сохраняется в событии."""
    return {"msp": {"schema": "msp-client-v1", "synthetic": "true", "run_id": run_id,
                    "case": scenario["case"], "tenant": scenario["tenant"],
                    "asset": scenario["asset"], "event": scenario["event"],
                    "status": scenario["status"], "approved": scenario["approved"],
                    "source": "training-fixture", "observed_at": datetime.now(timezone.utc).isoformat()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/home/service/wazuh-lab")
    args = parser.parse_args()
    root = Path(args.root)
    training = root / "training"
    if not (training / "business.jsonl").is_file() or not (training / "business-native.log").is_file():
        raise SystemExit("Сначала установить источники apply.py")
    scenarios = json.loads((Path(__file__).parent / "scenarios.json").read_text())
    run_id = str(uuid.uuid4())
    with (training / "business.jsonl").open("a", encoding="utf-8") as output:
        for item in scenarios:
            output.write(json.dumps(make_event(item, run_id), ensure_ascii=False) + "\n")
    # Формат sshd нужен штатному декодеру; только вымышленные адреса TEST-NET.
    stamp = datetime.now(timezone.utc).strftime("%b %d %H:%M:%S")
    user = "lab_" + run_id.replace("-", "")[:12]
    with (training / "business-native.log").open("a", encoding="utf-8") as output:
        output.write(f"{stamp} msp-business-native sshd[1234]: Failed password for {user} from 192.0.2.50 port 54321 ssh2\n")
        output.write(f"{stamp} msp-business-native sshd[1234]: Accepted publickey for {user} from 192.0.2.50 port 54321 ssh2\n")
    # Изменяется обычный безвредный файл в уже контролируемом каталоге FIM.
    fim = training / "fim/business-control.txt"
    fim.write_text("Synthetic business FIM exercise " + run_id + "\n")
    manifest = {"run_id": run_id, "generated_at": datetime.now(timezone.utc).isoformat(),
                "scenarios": scenarios, "native_user": user,
                "native_expected_rules": ["5760", "5715"], "fim_path": "/var/ossec/lab/fim/business-control.txt"}
    (root / "business-last-run.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("Набор записан. run_id=" + run_id)


if __name__ == "__main__":
    main()
