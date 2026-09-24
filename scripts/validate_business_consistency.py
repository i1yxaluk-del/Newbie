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
 if '24/7 engineer on-call не продаётся' not in text and path.name in {'PRICING.md','SALES_FUNNEL.md'}: pass
for required in ['## 10. SLA','## 12. Персональные данные','## 13. Ответственность','# ПРИЛОЖЕНИЕ 1. ORDER FORM','# ПРИЛОЖЕНИЕ 2. ПЕРИМЕТР','# ПРИЛОЖЕНИЕ 3. ПОРУЧЕНИЕ']:
 if required not in (ROOT/'contracts/MSP_SERVICE_AGREEMENT.md').read_text(encoding='utf-8'): errors.append('договор: нет '+required)
pricing=(ROOT/'commercial/PRICING.md').read_text(encoding='utf-8')
for value in ['25 000 ₽','50 000 ₽','3 500 ₽/ч','64,6%','63,5%']:
 if value not in pricing: errors.append('прайс: нет '+value)
landing=json.loads((ROOT/'frontend/src/content/landing.ru.json').read_text(encoding='utf-8'))
prices={p['id']:p['price'] for p in landing['pricing']['plans']}
if prices!={'bronze':'25 000','silver':'50 000','gold':'120 000'}: errors.append(f'landing prices {prices}')
if 'не равен круглосуточному дежурству' not in landing['pricing'].get('pricingFootnote',''): errors.append('landing: нет оговорки monitoring/on-call')
if errors:
 print('BUSINESS CONSISTENCY FAILED'); [print(' -',e) for e in errors]; sys.exit(1)
print('BUSINESS CONSISTENCY OK')
