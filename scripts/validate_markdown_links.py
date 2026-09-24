#!/usr/bin/env python3
"""Проверяет относительные ссылки в канонических MD-оглавлениях.

Junior: скрипт не ходит в интернет и не проверяет внешние URL. Он гарантирует,
что основные маршруты репозитория не ведут в удалённый файл или каталог.
"""
from pathlib import Path
from urllib.parse import unquote
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEXES = [
    'README.md', 'docs/README.md', 'docs/NAVIGATION.md',
    'commercial/README.md', 'contracts/README.md',
    'docs/deployment/README.md', 'docs/operations/README.md',
    'docs/training/README.md', 'docs/runbooks/README.md',
    'docs/checklists/README.md', 'deploy/README.md',
    'migration/README.md', 'services/README.md', 'scripts/README.md',
    'technical/README.md', 'infra/README.md',
]
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)]+)\)')
errors = []

for relative in INDEXES:
    page = ROOT / relative
    if not page.is_file():
        errors.append(f'{relative}: index отсутствует')
        continue
    text = page.read_text(encoding='utf-8')
    for raw in LINK.findall(text):
        target = raw.strip().split()[0].strip('<>')
        if target.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        path_part = unquote(target.split('#', 1)[0].split('?', 1)[0])
        if not path_part:
            continue
        resolved = (page.parent / path_part).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f'{relative}: ссылка выходит из репозитория: {target}')
            continue
        if not resolved.exists():
            errors.append(f'{relative}: тупиковая ссылка: {target}')

if errors:
    print('MARKDOWN NAVIGATION FAILED')
    for error in errors:
        print(' -', error)
    sys.exit(1)
print(f'MARKDOWN NAVIGATION OK: {len(INDEXES)} index-файлов')
