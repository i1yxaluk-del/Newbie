#!/usr/bin/env python3
"""Проверяет единый прайс, продажи, рекламу и договор."""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
FILES=[ROOT/'README.md',ROOT/'commercial/PRICING.md',ROOT/'commercial/SALES_FUNNEL.md',ROOT/'commercial/SALES_PLAYBOOK.md',ROOT/'commercial/ADS.md',ROOT/'commercial/PROPOSAL.md',ROOT/'contracts/MSP_SERVICE_AGREEMENT.md',ROOT/'technical/BUSINESS_MODEL.md']
errors=[]
for path in FILES:
 text=path.read_text(encoding='utf-8')
 if re.search(r'Gold.{0,80}85[\s\u00a0]?000',text,re.I|re.S): errors.append(f'{path}: старая цена Gold')
contract=(ROOT/'contracts/MSP_SERVICE_AGREEMENT.md').read_text(encoding='utf-8')
for required in ['## 10. SLA','## 12. Персональные данные','## 13. Ответственность','# ПРИЛОЖЕНИЕ 1. ORDER FORM','# ПРИЛОЖЕНИЕ 2. ПЕРИМЕТР','# ПРИЛОЖЕНИЕ 3. ПОРУЧЕНИЕ','GOLD ON DEMAND','Gold capacity approval']:
 if required not in contract: errors.append('договор: нет '+required)
pricing=(ROOT/'commercial/PRICING.md').read_text(encoding='utf-8')
for value in ['25 000 ₽','50 000 ₽','120 000 ₽','3 500 ₽/ч','64,6%','63,5%','53,4%','Gold capacity gate']:
 if value not in pricing: errors.append('прайс: нет '+value)
landing=json.loads((ROOT/'frontend/src/content/landing.ru.json').read_text(encoding='utf-8'))
prices={p['id']:p['price'] for p in landing['pricing']['plans']}
if prices!={'bronze':'25 000','silver':'50 000','gold':'120 000'}: errors.append(f'landing prices {prices}')
if 'не равен круглосуточному дежурству' not in landing['pricing'].get('pricingFootnote',''): errors.append('landing: нет оговорки monitoring/on-call')
# Проверять не только видимый JSON: SEO и публичные legal-страницы тоже обещают услугу.
public = ROOT/'frontend/public'
index = (public/'index.html').read_text(encoding='utf-8')
for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', index, re.S):
 data = json.loads(raw)
 if 'hasOfferCatalog' in data:
  offers = {p['name'].lower(): int(p['price']) for p in data['hasOfferCatalog']['itemListElement']}
  if offers != {key: int(value.replace(' ', '')) for key, value in prices.items()}:
   errors.append('SEO: цены расходятся с landing JSON')
for relative in ['docs/offer.html', 'docs/sla.html']:
 text = (public/relative).read_text(encoding='utf-8')
 for stale in ['85 000', '≤ 5 мин', '≤ 15 мин', '99.9%', '99,9%', 'скидка 10%', 'максимум 50%']:
  if stale in text: errors.append(f'{relative}: устаревшее обещание {stale}')
sla = (public/'docs/sla.html').read_text(encoding='utf-8')
for value in ['до 4 рабочих часов', 'до 2 рабочих часов', 'максимум 15%', '5%']:
 if value not in sla: errors.append('public SLA: нет '+value)
form = (ROOT/'frontend/src/components/sections/CTAForm.jsx').read_text(encoding='utf-8')
if '/docs/consent.html' not in form: errors.append('форма: нет отдельного согласия')
if 'Данные не передаются третьим лицам' in form: errors.append('форма: неверное обещание о получателях ПДн')
if not (public/'docs/consent.html').is_file(): errors.append('нет отдельного документа согласия')
# Читать цифры именно из таблицы, иначе изменение затрат останется незамеченным.
economics = pricing.split('## Экономическая проверка', 1)[1]
rows = {}
for line in economics.splitlines():
 if line.startswith('|'):
  cells = [cell.strip() for cell in line.strip('|').split('|')]
  if len(cells) == 4: rows[cells[0]] = cells[1:]
def amount(cell):
 match = re.search(r'[\d][\d\s]*(?:,\d+)?', cell)
 return float(match.group().replace(' ', '').replace(',', '.'))
for i, plan in enumerate(['bronze', 'silver', 'gold']):
 price, engineer, manager, tax, reserve, stated, margin = [amount(rows[key][i]) for key in
  ['Цена', 'Труд: инженер', 'Труд: service manager', 'Налог + банк, 7%', 'Резерв/переменные расходы', 'Contribution', 'Margin']]
 contribution = price - engineer - manager - tax - reserve
 if price != int(prices[plan].replace(' ', '')) or abs(tax-price*.07) > .01 or abs(contribution-stated) > .01 or abs(100*contribution/price-margin) > .051 or margin < 50:
  errors.append(f'экономика: неверная арифметика/маржа {plan}')
bot = (ROOT/'backend/integrations/max.py').read_text(encoding='utf-8')
for price in prices.values():
 if price not in bot: errors.append('MAX bot: нет цены '+price)
if 'capacity gate' not in bot: errors.append('MAX bot: нет capacity gate')
if errors:
 print('BUSINESS CONSISTENCY FAILED'); [print(' -',e) for e in errors]; sys.exit(1)
print('BUSINESS CONSISTENCY OK')
