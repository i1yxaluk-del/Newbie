#!/usr/bin/env python3
"""Проверить состав, воспроизводимость и актуальность ссылочных источников книги."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'book'
curriculum = json.loads((BOOK / 'curriculum.json').read_text(encoding='utf-8'))
manifest = json.loads((BOOK / 'manifest.json').read_text(encoding='utf-8'))
assert len(curriculum) == len(manifest['chapters']) == 22
assert {p.name for p in (BOOK/'chapters').glob('*.md')} == {i['file'] for i in curriculum}
for item, record in zip(curriculum, manifest['chapters']):
    for folder, key in [('lessons','lesson_sha256'),('chapters','chapter_sha256')]:
        raw = (BOOK/folder/item['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record[key], (folder,item['file'])
    for source in record['sources']:
        assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest() == source['sha256'], source['path']
print('DEEP_BOOK_OK chapters=22; lesson/chapter/source fingerprints match')
