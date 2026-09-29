from pathlib import Path
import re
r=Path(__file__).parent
fs=sorted((r/'chapters').glob('*.md'))
assert len(fs)==14, len(fs)
bad=['working tree','index/refs','развёртываниеment','commitment','clean target','customer','entry/exit','Проверьте себя','Учебная ситуация']
for f in fs:
 s=f.read_text(encoding='utf-8')
 assert len(s)>1000,(f,len(s))
 for x in bad: assert x not in s,(f,x)
 assert '## Видео' in s,(f,'video')
assert all(p.name in (r/'BOOK.md').read_text() for p in fs)
print('COMPLETE BOOK OK: 14 chapters')
