#!/usr/bin/env python3
"""Собрать книгу из редактируемых lessons и curriculum.json без копирования исходников.

Запуск из корня: python book/build_deep_book.py. Меняет только перечисленные главы,
оглавления и manifest; неизвестные файлы не удаляет. Старые generated главы до первой
сборки перемещаются в book/arhive/chapters_v1 с сохранением содержания.
"""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'book'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    curriculum = json.loads((BOOK / 'curriculum.json').read_text(encoding='utf-8'))
    chapters = BOOK / 'chapters'
    chapters.mkdir(exist_ok=True)
    expected = {item['file'] for item in curriculum}
    # Только прежние главы с известным маркером генератора; чужой текст не трогаем.
    for old in chapters.glob('*.md'):
        if old.name not in expected and '<!-- SOURCE ' in old.read_text(encoding='utf-8'):
            target = BOOK / 'arhive/chapters_v1' / old.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.read_bytes() != old.read_bytes():
                    raise SystemExit('Архив уже содержит другую версию: ' + old.name)
                old.unlink()
            else:
                shutil.move(old, target)
    manifest = {'format': 2, 'chapters': []}
    contents = ['# MSPShield: книга владельца и начинающего маркетолога', '',
                '[Маршруты читателей](READING_PATHS.md) · [Текущая картина проекта](CURRENT_STATE.md) · [Обучение и видео](VIDEO_GUIDE.md)', '',
                'Редактируемые объяснения находятся в `lessons/`; главы собраны из них. Рабочие инструкции и код открываются по ссылкам, а не копируются целиком. Состояние VM подтверждается датированным отчётом, не текстом учебника.', '', '## Главы', '']
    source_rows = ['# Карта источников книги', '', '| Глава | Канонические документы и код |', '|---|---|']
    for index, item in enumerate(curriculum):
        lesson = BOOK / 'lessons' / item['file']
        intro = lesson.read_text(encoding='utf-8')
        source_records = []
        links = []
        for relative in item['sources']:
            path = ROOT / relative
            if not path.is_file():
                raise SystemExit('Источник отсутствует: ' + relative)
            source_records.append({'path': relative, 'sha256': digest(path)})
            links.append(f'- [`{relative}`](../../{relative})')
        text = f'# {item["title"]}\n\n[← Оглавление](../BOOK.md) · [Маршруты](../READING_PATHS.md) · [Уроки и видео](../VIDEO_GUIDE.md)\n\n'
        # В уроках ссылки относительно будущей chapters/, обе папки одного уровня.
        text += intro.strip() + '\n\n## Где это реализовано в проекте\n\n' + '\n'.join(links) + '\n'
        if index + 1 < len(curriculum):
            text += f'\n[Следующая глава: {curriculum[index+1]["title"]}]({curriculum[index+1]["file"]})\n'
        target = chapters / item['file']
        target.write_text(text, encoding='utf-8')
        manifest['chapters'].append({'file': item['file'], 'lesson_sha256': digest(lesson), 'chapter_sha256': digest(target), 'sources': source_records})
        contents.append(f'{index+1}. [{item["title"]}](chapters/{item["file"]})')
        source_rows.append(f'| [{item["title"]}](chapters/{item["file"]}) | ' + ', '.join(f'[`{r}`](../{r})' for r in item['sources']) + ' |')
    contents += ['', '## Справочники', '', '- [Технологии и обучение](STACK_AND_LEARNING.md)', '- [Клиентский стек, российское ПО и видео](CLIENT_STACK_ACADEMY.md)', '- [Управление, продажи и клиентские разговоры](MANAGEMENT_PRACTICE.md)', '- [Бизнес-процессы и передача работы](PROCESS_MAP.md)', '- [Словарь](GLOSSARY.md)', '- [Проверка тарифа](TARIFF_DECISION.md)', '- [Проверки книги](GATES.md)', '- [Связность](CONTINUITY.md)', '- [Карта источников](SOURCE_MAP.md)']
    (BOOK / 'BOOK.md').write_text('\n'.join(contents) + '\n', encoding='utf-8')
    (BOOK / 'SOURCE_MAP.md').write_text('\n'.join(source_rows) + '\n', encoding='utf-8')
    (BOOK / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'BOOK_BUILT chapters={len(curriculum)}; sources referenced, not embedded')


if __name__ == '__main__':
    build()
