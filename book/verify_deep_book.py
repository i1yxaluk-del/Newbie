from pathlib import Path
import re,hashlib
r=Path(__file__).resolve().parents[1]; b=r/'book'; fs=sorted((b/'chapters').glob('*.md'))
assert len(fs)==18,len(fs)
alltext='\n'.join(x.read_text(encoding='utf-8') for x in fs)
for term in ['RPO','RTO','SLA','MSA','Outbox','Gold Capacity Check','offboarding','postmortem','auth --authorize','preflight.sh']:
 assert term.lower() in alltext.lower(),term
for p,d in re.findall(r'<!-- SOURCE ([^ ]+) ([0-9a-f]{16}) -->',alltext):
 raw=(r/p).read_text(encoding='utf-8-sig'); assert hashlib.sha256(raw.encode()).hexdigest()[:16]==d,p
for f in fs: assert len(f.read_text(encoding='utf-8'))>2500,(f,len(f.read_text()))
for name in ['BOOK.md','GLOSSARY.md','TARIFF_DECISION.md','SOURCE_MAP.md','CONTINUITY.md','GATES.md']: assert (b/name).exists(),name
assert 'working tree/index/refs' not in alltext
print(f'DEEP_BOOK_OK chapters={len(fs)} sources={alltext.count("<!-- SOURCE ")} chars={len(alltext)}')
