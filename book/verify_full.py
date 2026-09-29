from pathlib import Path
from collections import Counter
import re,sys,json
R=Path('/data/MSPShield_Academy_MD'); C=R/'chapters'; fs=sorted(C.glob('*.md')); book=(R/'BOOK.md').read_text(); texts=[f.read_text() for f in fs]; alltext='\n'.join(texts)
def req(x,m):
 if not x: raise SystemExit('FAIL '+m)
req(len(fs)==38,'chapter count')
req(len(json.loads((R/'manifest.json').read_text()))==38,'manifest')
for f,t in zip(fs,texts):
 req(len(t.split())>=450,f'{f.name} too short')
 for h in ['## Модель, которую нужно построить','## Термины в рабочем смысле','## Что происходит внутри','## Разобранный пример','## Практикум','## Если результат не совпал с ожиданием','## Самостоятельная работа','## Источники проекта']:
  req(h in t,f'{f.name} missing {h}')
 req(t.count('```')>=2,f'{f.name} no code example')
 req('89249e43a4e8b2e90d562307ef244ba95288c64c' in t,f'{f.name} unpinned links')
req('\ufffd' not in alltext+book,'replacement chars')
req(not re.search(r'\b(TODO|TBD|PLACEHOLDER)\b',alltext,re.I),'placeholders')
for link in re.findall(r'\]\((?!https?://)([^)#]+)',book): req((R/link).exists(),f'broken book link {link}')
# No long boilerplate line may occur in 10+ chapters.
lines=Counter(line.strip() for t in texts for line in t.splitlines() if len(line.strip())>120)
req(not [(l,n) for l,n in lines.items() if n>=10], 'repeated boilerplate')
for term in ['maxapi-python','Stalwart','Postbox','RPO','contribution','Gold','CAC','LTV','capacity','outbox']:
 req(term.lower() in alltext.lower(),f'missing {term}')
print('FULL_BOOK_OK chapters=38 words='+str(len(alltext.split()))+' links='+str(alltext.count('](')))
