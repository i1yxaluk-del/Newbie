"""Сборка всех документов пакета v2 в одной команде."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
MODULES = [
    "build_01_master.py",
    "build_02_tariffs.py",
    "build_03_sla.py",
    "build_04_perimetr.py",
    "build_05_pdn.py",
    "build_06_nda.py",
    "build_07_akt.py",
    "build_08_peredacha.py",
]


def main():
    rc = 0
    for m in MODULES:
        path = HERE / m
        print(f"=> {m}")
        result = subprocess.run([sys.executable, str(path)], cwd=str(HERE))
        if result.returncode != 0:
            print(f"!! failed: {m}")
            rc = result.returncode
    print()
    print("Build finished. Files:")
    build_dir = HERE / "build"
    if build_dir.exists():
        for f in sorted(build_dir.iterdir()):
            print(f"  - {f.name} ({f.stat().st_size:,} bytes)")
    sys.exit(rc)


if __name__ == "__main__":
    main()
