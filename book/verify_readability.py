#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parent
files=list((R/'chapters').glob('*.md'))
text='\n'.join(p.read_text(encoding="utf-8-sig") for p in files)
bad=['Git-команда читает или изменяет','Разделите строку на программу','Это сужает область поиска','steady сохранённые данные','развёртываниеment']
errors=[x for x in bad if x in text]
if errors: raise SystemExit('BAD PHRASES: '+', '.join(errors))
if '--yandex' in sys.argv:
 y=(R/'chapters/17-облако-и-vm-с-нуля.md').read_text()
 for x in ['Облако','Каталог','Виртуальная машина','Зона доступности','Группа безопасности','Сервисная учётная запись','## Видео','## Практика']:
  if x not in y: raise SystemExit('YANDEX MISSING '+x)
 print('YANDEX CHAPTER OK')
else:
 print('BOOK READABILITY OK')
