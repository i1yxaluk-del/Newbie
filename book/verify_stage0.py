from pathlib import Path
import re,sys
r=Path('/data/MSPShield_Academy_MD')
book=(r/'00_BOOK_MAP.md').read_text(); std=(r/'00_AUTHORING_STANDARD.md').read_text(); mode=sys.argv[1]
def ok(token): print(token)
def require(cond,msg):
 if not cond: raise SystemExit('FAIL: '+msg)
if mode=='structure':
 require(len(re.findall(r'^## \d+\.',book,re.M))==38,'expected 38 chapters')
 require(all(x in book for x in ['Технический capstone','Финальный бизнес-capstone','Порядок написания глав']),'missing progression')
 ok('STRUCTURE_OK')
elif mode=='repository':
 for x in ['89249e43','maxapi-python','2.4.1','Caddy','Stalwart','Postbox','AWG','TCP-доступность']:
  require(x in std+book,x)
 ok('REPOSITORY_OK')
elif mode=='business':
 for x in ['contribution','capacity','margin','ICP','Воронка','SLA','MRR','CAC','LTV']:
  require(x.lower() in book.lower(),x)
 require(book.index('# Часть VI.')>book.index('Технический capstone'),'business before technical mastery')
 ok('BUSINESS_OK')
elif mode=='pedagogy':
 for x in ['Worked example','guidance fading','cognitive load','Retrieval practice','Mastery gates','словари']:
  require(x.lower() in std.lower(),x)
 require('Заголовка «Проверяемые результаты» не будет' in std,'bad heading policy')
 ok('PEDAGOGY_OK')
elif mode=='factuality':
 for x in ['REPO FACT','EXTERNAL FACT','MODEL','ASSUMPTION']:
  require(x in std,x)
 ok('FACTUALITY_OK')
elif mode=='chapters':
 blocks=re.split(r'^## \d+\.',book,flags=re.M)[1:]
 require(len(blocks)==38,'blocks')
 for i,b in enumerate(blocks,1):
  for x in ['**Опора:**','**Разбираем:**','**Практика:**','**На выходе:**']:
   require(x in b,f'{i} {x}')
 ok('CHAPTERS_OK')
else: raise SystemExit('unknown')
