#!/usr/bin/env python3
"""Структурные признаки учебных глав, не автоматическая оценка понимания человека."""
import json
from pathlib import Path
BOOK=Path(__file__).resolve().parent
items=json.loads((BOOK/'curriculum.json').read_text(encoding='utf-8'))
for item in items:
    text=(BOOK/'chapters'/item['file']).read_text(encoding='utf-8')
    assert len(text)>1400,item['file']
    assert text.count('\n## ')>=3,item['file']
    assert 'практик' in text.lower() or 'экзамен' in text.lower(),item['file']
    assert '<!-- SOURCE ' not in text,item['file']
    assert item['file'] in (BOOK/'BOOK.md').read_text(encoding='utf-8'),item['file']
for name in ['READING_PATHS.md','CURRENT_STATE.md','PROCESS_MAP.md','STACK_AND_LEARNING.md','VIDEO_GUIDE.md']:
    assert (BOOK/name).is_file(),name
print(f'BOOK_STRUCTURE_OK chapters={len(items)}; human review still required')
