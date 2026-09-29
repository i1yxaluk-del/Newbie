#!/usr/bin/env python3
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]; e=[]
def t(f): return (R/f).read_text(encoding="utf-8-sig")
def n(f,s):
 if s not in t(f): e.append(f"{f}: missing {s}")
def b(f,s):
 if s in t(f): e.append(f"{f}: stale {s}")
n("deploy/yandex/docker-compose.yml","127.0.0.1:8001:8001"); b("deploy/yandex/Caddyfile","0.0.0.0:8001:8001")
n("services/max_alerter/requirements.txt","maxapi-python==2.4.1"); n("docs/MAX_SETUP.md","auth --authorize")
n("book/chapters/21-alerting-и-доставка-в-max.md","auth --authorize"); b("backend/.env.example","используется long-polling")
n("technical/0_Common/SERVICES/mail_dns.md","CNAME_N="); b("deploy/yandex/STALWART_RELAY_MODE.md","Скопируйте TXT и положите в DNS")
b("docs/deployment/secrets_management.md","python3 auth.py --phone")
for f in ["infra/terraform/cloud-init/landing.yaml","infra/terraform/cloud-init/bastion.yaml"]: n(f,"TEMP bootstrap SSH")
if e:
 print("DEPLOYMENT FRESHNESS FAILED",*e,sep="\n - "); sys.exit(1)
print("DEPLOYMENT FRESHNESS OK")
