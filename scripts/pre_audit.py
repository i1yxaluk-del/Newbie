#!/usr/bin/env python3
"""
Автоматический пре-аудит внешнего периметра клиента по домену.

Собирает данные из открытых источников (без доступа к внутренней сети)
и формирует pre-audit лист для вставки в Kaiten-карточку.

Проверки:
  1. WHOIS (регистратор, срок, возраст домена)
  2. DNS-резолв (A, AAAA, NS, CNAME)
  3. SSL-сертификат (издатель, срок действия, SAN)
  4. Почта: MX / SPF / DMARC / DKIM (selector: default)
  5. HTTP-доступность и заголовки безопасности
  6. Открытые порты (TCP connect, top-30)
  7. Проверка домена по RBL-спискам
  8. HIBP — публичные утечки по домену

Запуск:
    pip install dnspython httpx python-whois
    python scripts/pre_audit.py example.ru

Результат выводится в stdout (Markdown). Перенаправьте в файл:
    python scripts/pre_audit.py example.ru > pre_audit_example_ru.md

⚠  Скрипт выполняет ТОЛЬКО пассивные проверки публично доступных сервисов.
   Внутренняя сеть и сервисы за NAT НЕ затрагиваются.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import socket
import ssl
import sys
import textwrap
from datetime import datetime, timezone
from typing import Any

import dns.resolver
import httpx
import whois


# ─── Константы ────────────────────────────────────────────────────────

TOP_PORTS: dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    111: "RPCbind",
    135: "MSRPC",
    139: "NetBIOS",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    465: "SMTPS",
    587: "Submission",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "Oracle",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    8080: "HTTP-alt",
    8443: "HTTPS-alt",
    8888: "HTTP-alt2",
    9090: "Prometheus",
    9200: "Elasticsearch",
    27017: "MongoDB",
}

RBL_LISTS: list[str] = [
    "zen.spamhaus.org",
    "bl.spamcop.net",
    "b.barracudacentral.org",
    "dnsbl.sorbs.net",
    "spam.dnsbl.sorbs.net",
    "dnsbl-1.uceprotect.net",
    "psbl.surriel.com",
    "all.s5h.net",
]

SECURITY_HEADERS: list[str] = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "X-XSS-Protection",
    "Referrer-Policy",
    "Permissions-Policy",
]

PORT_SCAN_TIMEOUT = 2.0
HTTP_TIMEOUT = 10.0


# ─── Утилиты ─────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def _days_left(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - datetime.now(timezone.utc)).days


def _risk_badge(is_risk: bool) -> str:
    return "🔴" if is_risk else "🟢"


# ─── 1. WHOIS ────────────────────────────────────────────────────────

def check_whois(domain: str) -> dict[str, Any]:
    """Запрос WHOIS: регистратор, даты, статус."""
    result: dict[str, Any] = {"ok": False}
    try:
        w = whois.whois(domain)
        creation = w.creation_date
        expiration = w.expiration_date
        if isinstance(creation, list):
            creation = creation[0]
        if isinstance(expiration, list):
            expiration = expiration[0]

        result["registrar"] = w.registrar or "—"
        result["creation_date"] = creation.strftime("%d.%m.%Y") if creation else "—"
        result["expiration_date"] = expiration.strftime("%d.%m.%Y") if expiration else "—"
        result["days_until_expiry"] = _days_left(expiration) if expiration else None
        result["name_servers"] = w.name_servers if w.name_servers else []
        result["status"] = w.status if w.status else []
        result["ok"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


# ─── 2. DNS ──────────────────────────────────────────────────────────

def check_dns(domain: str) -> dict[str, Any]:
    """DNS-резолв: A, AAAA, NS, CNAME."""
    result: dict[str, Any] = {}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 10

    for rtype in ("A", "AAAA", "NS", "CNAME"):
        try:
            answers = resolver.resolve(domain, rtype)
            result[rtype] = [str(r) for r in answers]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            result[rtype] = []
        except dns.resolver.NoNameservers:
            result[rtype] = ["⚠ нет ответа от NS"]
        except Exception:
            result[rtype] = []

    return result


# ─── 3. SSL ──────────────────────────────────────────────────────────

def check_ssl(domain: str) -> dict[str, Any]:
    """Получить SSL-сертификат и проверить сроки."""
    result: dict[str, Any] = {"ok": False}
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
                days = _days_left(not_after)

                result["issuer"] = dict(x[0] for x in cert.get("issuer", []))
                result["subject"] = dict(x[0] for x in cert.get("subject", []))
                result["not_before"] = not_before.strftime("%d.%m.%Y")
                result["not_after"] = not_after.strftime("%d.%m.%Y")
                result["days_left"] = days
                result["san"] = [
                    e[1] for e in cert.get("subjectAltName", []) if e[0] == "DNS"
                ]
                result["serial"] = cert.get("serialNumber", "—")
                result["version"] = ssock.version()
                result["ok"] = True
    except ssl.SSLCertVerificationError as e:
        result["error"] = f"Ошибка верификации: {e}"
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        result["error"] = f"Не удалось подключиться к :443 — {e}"
    return result


# ─── 4. Почта: MX / SPF / DMARC / DKIM ─────────────────────────────

def check_mail(domain: str) -> dict[str, Any]:
    """MX-записи, SPF, DMARC, DKIM (selector=default)."""
    result: dict[str, Any] = {}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 10

    # MX
    try:
        mx_answers = resolver.resolve(domain, "MX")
        result["mx"] = sorted(
            [(r.preference, str(r.exchange).rstrip(".")) for r in mx_answers]
        )
    except Exception:
        result["mx"] = []

    # SPF (TXT)
    result["spf"] = None
    try:
        txt_answers = resolver.resolve(domain, "TXT")
        for r in txt_answers:
            txt = r.to_text().strip('"')
            if txt.lower().startswith("v=spf1"):
                result["spf"] = txt
                break
    except Exception:
        pass

    # DMARC
    result["dmarc"] = None
    try:
        dmarc_answers = resolver.resolve(f"_dmarc.{domain}", "TXT")
        for r in dmarc_answers:
            txt = r.to_text().strip('"')
            if "v=dmarc" in txt.lower():
                result["dmarc"] = txt
                break
    except Exception:
        pass

    # DKIM (selector: default)
    result["dkim"] = None
    for selector in ("default", "google", "mail", "selector1", "selector2"):
        try:
            dkim_answers = resolver.resolve(f"{selector}._domainkey.{domain}", "TXT")
            for r in dkim_answers:
                txt = r.to_text().strip('"')
                if "v=dkim" in txt.lower() or "p=" in txt:
                    result["dkim"] = f"[{selector}] {txt[:80]}…" if len(txt) > 80 else f"[{selector}] {txt}"
                    break
            if result["dkim"]:
                break
        except Exception:
            pass

    return result


# ─── 5. HTTP-доступность и заголовки ────────────────────────────────

def check_http(domain: str) -> dict[str, Any]:
    """HTTP/HTTPS доступность, редиректы, заголовки безопасности."""
    result: dict[str, Any] = {}

    for scheme in ("https", "http"):
        key = scheme
        url = f"{scheme}://{domain}"
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True, verify=False) as client:
                r = client.get(url)
                entry: dict[str, Any] = {
                    "status": r.status_code,
                    "final_url": str(r.url),
                    "server": r.headers.get("server", "—"),
                    "redirects": len(r.history),
                }

                # Заголовки безопасности
                sec: dict[str, str | None] = {}
                for h in SECURITY_HEADERS:
                    sec[h] = r.headers.get(h)
                entry["security_headers"] = sec
                result[key] = entry
        except Exception as e:
            result[key] = {"error": str(e)}

    return result


# ─── 6. Порты ────────────────────────────────────────────────────────

def _scan_port(ip: str, port: int) -> tuple[int, str, bool]:
    """Проверить один TCP-порт (connect scan)."""
    try:
        with socket.create_connection((ip, port), timeout=PORT_SCAN_TIMEOUT):
            return port, TOP_PORTS.get(port, "unknown"), True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return port, TOP_PORTS.get(port, "unknown"), False


def check_ports(domain: str) -> dict[str, Any]:
    """TCP connect scan top-30 портов."""
    result: dict[str, Any] = {"ip": None, "open": []}
    try:
        ip = socket.gethostbyname(domain)
        result["ip"] = ip
    except socket.gaierror as e:
        result["error"] = str(e)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:
        futures = {pool.submit(_scan_port, ip, p): p for p in TOP_PORTS}
        for f in concurrent.futures.as_completed(futures):
            port, service, is_open = f.result()
            if is_open:
                result["open"].append({"port": port, "service": service})

    result["open"].sort(key=lambda x: x["port"])
    return result


# ─── 7. RBL ──────────────────────────────────────────────────────────

def check_rbl(domain: str) -> dict[str, Any]:
    """Проверить IP домена по основным RBL-спискам."""
    result: dict[str, Any] = {"listed": [], "clean": [], "ip": None}
    try:
        ip = socket.gethostbyname(domain)
        result["ip"] = ip
    except socket.gaierror:
        result["error"] = "Не удалось определить IP"
        return result

    reversed_ip = ".".join(reversed(ip.split(".")))
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3
    resolver.lifetime = 5

    for rbl in RBL_LISTS:
        query = f"{reversed_ip}.{rbl}"
        try:
            resolver.resolve(query, "A")
            result["listed"].append(rbl)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            result["clean"].append(rbl)
        except Exception:
            result["clean"].append(rbl)

    return result


# ─── 8. HIBP (публичные утечки) ──────────────────────────────────────

def check_hibp(domain: str) -> dict[str, Any]:
    """Проверить домен в Have I Been Pwned (публичный API — breaches по домену)."""
    result: dict[str, Any] = {"breaches": [], "ok": False}
    # Публичный API: список всех утечек, фильтр по домену
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            r = client.get(
                "https://haveibeenpwned.com/api/v3/breaches",
                headers={"User-Agent": "MSPShield-PreAudit/1.0"},
            )
            if r.status_code == 200:
                all_breaches = r.json()
                # Фильтруем: утечки, в которых фигурирует этот домен
                for b in all_breaches:
                    if domain.lower() == b.get("Domain", "").lower():
                        result["breaches"].append({
                            "name": b.get("Name"),
                            "date": b.get("BreachDate"),
                            "count": b.get("PwnCount"),
                            "data_classes": b.get("DataClasses", []),
                        })
                result["ok"] = True
                result["note"] = (
                    "Проверен домен в базе HIBP. Для проверки конкретных email-адресов "
                    "требуется платный API-ключ (https://haveibeenpwned.com/API/Key)."
                )
            else:
                result["error"] = f"HTTP {r.status_code}"
    except Exception as e:
        result["error"] = str(e)
    return result


# ─── Формирование отчёта (Markdown) ──────────────────────────────────

def format_report(
    domain: str,
    whois_data: dict,
    dns_data: dict,
    ssl_data: dict,
    mail_data: dict,
    http_data: dict,
    ports_data: dict,
    rbl_data: dict,
    hibp_data: dict,
) -> str:
    """Собрать Markdown-отчёт из всех проверок."""
    lines: list[str] = []

    def ln(text: str = "") -> None:
        lines.append(text)

    # ─── Шапка ────────────────────────────────────────────────────
    ln(f"# Pre-audit лист: `{domain}`")
    ln()
    ln(f"| | |")
    ln(f"|---|---|")
    ln(f"| **Дата** | {_now()} |")
    ln(f"| **Домен** | `{domain}` |")
    if ports_data.get("ip"):
        ln(f"| **IP** | `{ports_data['ip']}` |")
    ln(f"| **Метод** | Внешний автоматический аудит (пассивный) |")
    ln()

    # ─── Быстрая сводка рисков ─────────────────────────────────
    risks: list[str] = []

    # SSL
    if ssl_data.get("ok"):
        if ssl_data["days_left"] < 30:
            risks.append(f"🔴 SSL истекает через {ssl_data['days_left']} дн.")
        elif ssl_data["days_left"] < 60:
            risks.append(f"🟡 SSL истекает через {ssl_data['days_left']} дн.")
    elif ssl_data.get("error"):
        risks.append("🔴 SSL — ошибка подключения / верификации")

    # Почта
    if not mail_data.get("spf"):
        risks.append("🔴 SPF не настроен — возможен спуфинг")
    if not mail_data.get("dmarc"):
        risks.append("🔴 DMARC не настроен — нет защиты от подделки писем")
    if not mail_data.get("mx"):
        risks.append("🟡 MX не найден — почта не настроена?")

    # RBL
    if rbl_data.get("listed"):
        risks.append(f"🔴 IP в {len(rbl_data['listed'])} чёрных списках")

    # HIBP
    if hibp_data.get("breaches"):
        risks.append(f"🟡 Домен фигурирует в {len(hibp_data['breaches'])} утечках (HIBP)")

    # Порты
    risky_ports = [p for p in ports_data.get("open", []) if p["port"] in (23, 135, 139, 445, 3389, 5900, 6379, 27017, 9200)]
    if risky_ports:
        names = ", ".join(f"{p['port']}/{p['service']}" for p in risky_ports)
        risks.append(f"🔴 Опасные порты открыты: {names}")

    # WHOIS
    if whois_data.get("days_until_expiry") is not None and whois_data["days_until_expiry"] < 30:
        risks.append(f"🟡 Домен истекает через {whois_data['days_until_expiry']} дн.")

    # HTTP security headers
    https_entry = http_data.get("https", {})
    if isinstance(https_entry, dict) and "security_headers" in https_entry:
        missing = [h for h, v in https_entry["security_headers"].items() if v is None]
        if len(missing) >= 5:
            risks.append(f"🟡 Отсутствуют {len(missing)} из {len(SECURITY_HEADERS)} заголовков безопасности")

    if risks:
        ln("## ⚡ Сводка рисков")
        ln()
        for r in risks:
            ln(f"- {r}")
        ln()
    else:
        ln("## ✅ Критичных рисков не обнаружено")
        ln()

    # ─── 1. WHOIS ────────────────────────────────────────────────
    ln("---")
    ln("## 1. WHOIS")
    ln()
    if whois_data.get("ok"):
        ln(f"| Параметр | Значение |")
        ln(f"|----------|----------|")
        ln(f"| Регистратор | {whois_data['registrar']} |")
        ln(f"| Дата регистрации | {whois_data['creation_date']} |")
        ln(f"| Дата окончания | {whois_data['expiration_date']} |")
        if whois_data.get("days_until_expiry") is not None:
            badge = _risk_badge(whois_data["days_until_expiry"] < 30)
            ln(f"| До окончания | {badge} {whois_data['days_until_expiry']} дн. |")
        if whois_data.get("name_servers"):
            ns_list = whois_data["name_servers"]
            if isinstance(ns_list, list):
                ns_str = ", ".join(str(s).lower() for s in ns_list[:4])
            else:
                ns_str = str(ns_list)
            ln(f"| NS | {ns_str} |")
    else:
        ln(f"⚠ Ошибка WHOIS: {whois_data.get('error', 'н/д')}")
    ln()

    # ─── 2. DNS ──────────────────────────────────────────────────
    ln("---")
    ln("## 2. DNS")
    ln()
    ln(f"| Тип | Записи |")
    ln(f"|-----|--------|")
    for rtype in ("A", "AAAA", "NS", "CNAME"):
        records = dns_data.get(rtype, [])
        val = ", ".join(f"`{r}`" for r in records) if records else "—"
        ln(f"| {rtype} | {val} |")
    ln()

    # ─── 3. SSL ──────────────────────────────────────────────────
    ln("---")
    ln("## 3. SSL-сертификат")
    ln()
    if ssl_data.get("ok"):
        days = ssl_data["days_left"]
        badge = "🟢" if days >= 60 else ("🟡" if days >= 30 else "🔴")
        ln(f"| Параметр | Значение |")
        ln(f"|----------|----------|")
        ln(f"| Издатель | {ssl_data['issuer'].get('organizationName', ssl_data['issuer'].get('commonName', '—'))} |")
        ln(f"| CN | {ssl_data['subject'].get('commonName', '—')} |")
        ln(f"| Действителен с | {ssl_data['not_before']} |")
        ln(f"| Действителен до | {ssl_data['not_after']} |")
        ln(f"| Осталось дней | {badge} {days} |")
        ln(f"| TLS версия | {ssl_data['version']} |")
        if ssl_data.get("san"):
            san_str = ", ".join(f"`{s}`" for s in ssl_data["san"][:5])
            if len(ssl_data["san"]) > 5:
                san_str += f" (+{len(ssl_data['san']) - 5})"
            ln(f"| SAN | {san_str} |")
    else:
        ln(f"⚠ {ssl_data.get('error', 'Не удалось получить сертификат')}")
    ln()

    # ─── 4. Почта ────────────────────────────────────────────────
    ln("---")
    ln("## 4. Почта (MX / SPF / DMARC / DKIM)")
    ln()

    # MX
    if mail_data.get("mx"):
        ln("**MX-записи:**")
        for pref, exch in mail_data["mx"]:
            ln(f"- `{pref}` → `{exch}`")
    else:
        ln("**MX:** ⚠ не найдены")
    ln()

    # SPF
    if mail_data.get("spf"):
        ln(f"**SPF:** `{mail_data['spf']}`")
    else:
        ln(f"**SPF:** {_risk_badge(True)} не настроен")
    ln()

    # DMARC
    if mail_data.get("dmarc"):
        ln(f"**DMARC:** `{mail_data['dmarc']}`")
    else:
        ln(f"**DMARC:** {_risk_badge(True)} не настроен")
    ln()

    # DKIM
    if mail_data.get("dkim"):
        ln(f"**DKIM:** `{mail_data['dkim']}`")
    else:
        ln(f"**DKIM:** не найден (проверены селекторы: default, google, mail, selector1, selector2)")
    ln()

    # ─── 5. HTTP ─────────────────────────────────────────────────
    ln("---")
    ln("## 5. HTTP-доступность и заголовки")
    ln()
    for scheme in ("https", "http"):
        entry = http_data.get(scheme, {})
        if "error" in entry:
            ln(f"**{scheme.upper()}:** ⚠ {entry['error']}")
        elif "status" in entry:
            ln(f"**{scheme.upper()}:** `{entry['status']}` → `{entry['final_url']}`")
            if entry.get("server") != "—":
                ln(f"- Server: `{entry['server']}`")
            if entry.get("redirects", 0) > 0:
                ln(f"- Редиректов: {entry['redirects']}")
        ln()

    # Заголовки безопасности
    https_entry = http_data.get("https", {})
    if isinstance(https_entry, dict) and "security_headers" in https_entry:
        ln("**Заголовки безопасности:**")
        ln()
        ln("| Заголовок | Статус |")
        ln("|-----------|--------|")
        for h in SECURITY_HEADERS:
            val = https_entry["security_headers"].get(h)
            if val:
                ln(f"| {h} | ✅ `{val[:60]}{'…' if len(val) > 60 else ''}` |")
            else:
                ln(f"| {h} | ❌ отсутствует |")
        ln()

    # ─── 6. Порты ────────────────────────────────────────────────
    ln("---")
    ln("## 6. Открытые порты (TCP connect, top-30)")
    ln()
    if ports_data.get("error"):
        ln(f"⚠ {ports_data['error']}")
    elif ports_data.get("open"):
        ln(f"IP: `{ports_data['ip']}`")
        ln()
        ln("| Порт | Сервис | Заметка |")
        ln("|------|--------|---------|")
        dangerous = {23: "⚠ Telnet — небезопасный протокол", 135: "⚠ MSRPC", 139: "⚠ NetBIOS",
                     445: "⚠ SMB — частая цель атак", 3389: "⚠ RDP — частая цель брутфорса",
                     5900: "⚠ VNC", 6379: "⚠ Redis — часто без пароля",
                     27017: "⚠ MongoDB — часто без авторизации",
                     9200: "⚠ Elasticsearch — часто без авторизации"}
        for p in ports_data["open"]:
            note = dangerous.get(p["port"], "")
            ln(f"| {p['port']} | {p['service']} | {note} |")
    else:
        ln(f"IP: `{ports_data.get('ip', '—')}` — открытых портов из top-30 не обнаружено.")
    ln()

    # ─── 7. RBL ──────────────────────────────────────────────────
    ln("---")
    ln("## 7. Чёрные списки (RBL)")
    ln()
    if rbl_data.get("error"):
        ln(f"⚠ {rbl_data['error']}")
    elif rbl_data.get("listed"):
        ln(f"IP `{rbl_data['ip']}` найден в {len(rbl_data['listed'])} списках:")
        ln()
        for rbl in rbl_data["listed"]:
            ln(f"- 🔴 `{rbl}`")
    else:
        ln(f"✅ IP `{rbl_data.get('ip', '—')}` чист — проверено {len(rbl_data.get('clean', []))} RBL-списков.")
    ln()

    # ─── 8. HIBP ─────────────────────────────────────────────────
    ln("---")
    ln("## 8. Публичные утечки (HIBP)")
    ln()
    if hibp_data.get("error"):
        ln(f"⚠ {hibp_data['error']}")
    elif hibp_data.get("breaches"):
        ln(f"Домен `{domain}` фигурирует в {len(hibp_data['breaches'])} утечках:")
        ln()
        ln("| Утечка | Дата | Кол-во записей | Данные |")
        ln("|--------|------|----------------|--------|")
        for b in hibp_data["breaches"]:
            data_str = ", ".join(b["data_classes"][:3])
            if len(b["data_classes"]) > 3:
                data_str += "…"
            count = f"{b['count']:,}".replace(",", " ") if b["count"] else "—"
            ln(f"| {b['name']} | {b['date']} | {count} | {data_str} |")
    else:
        ln(f"✅ Домен `{domain}` не найден в базе утечек HIBP.")
    if hibp_data.get("note"):
        ln()
        ln(f"_{hibp_data['note']}_")
    ln()

    # ─── Подвал ──────────────────────────────────────────────────
    ln("---")
    ln()
    ln(f"_Отчёт сгенерирован автоматически · MSPShield pre_audit.py · {_now()}_")
    ln(f"_Только внешние пассивные проверки. Не заменяет полноценный пентест._")

    return "\n".join(lines)


# ─── main ─────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MSPShield — автоматический пре-аудит внешнего периметра клиента.",
        epilog="Пример: python scripts/pre_audit.py example.ru",
    )
    parser.add_argument("domain", help="Домен клиента (например, company.ru)")
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Вывести результат в JSON вместо Markdown",
    )
    args = parser.parse_args()

    domain = args.domain.strip().lower()
    # Убираем протокол, если передали URL
    for prefix in ("https://", "http://", "www."):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    domain = domain.rstrip("/")

    print(f"⏳ Запускаю пре-аудит для {domain}...", file=sys.stderr)

    # Параллельный сбор данных
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        f_whois = pool.submit(check_whois, domain)
        f_dns = pool.submit(check_dns, domain)
        f_ssl = pool.submit(check_ssl, domain)
        f_mail = pool.submit(check_mail, domain)
        f_http = pool.submit(check_http, domain)
        f_ports = pool.submit(check_ports, domain)
        f_rbl = pool.submit(check_rbl, domain)
        f_hibp = pool.submit(check_hibp, domain)

    whois_data = f_whois.result()
    dns_data = f_dns.result()
    ssl_data = f_ssl.result()
    mail_data = f_mail.result()
    http_data = f_http.result()
    ports_data = f_ports.result()
    rbl_data = f_rbl.result()
    hibp_data = f_hibp.result()

    print(f"✅ Проверки завершены.", file=sys.stderr)

    if args.json_output:
        output = json.dumps(
            {
                "domain": domain,
                "timestamp": _now(),
                "whois": whois_data,
                "dns": dns_data,
                "ssl": ssl_data,
                "mail": mail_data,
                "http": http_data,
                "ports": ports_data,
                "rbl": rbl_data,
                "hibp": hibp_data,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        print(output)
    else:
        report = format_report(
            domain, whois_data, dns_data, ssl_data, mail_data,
            http_data, ports_data, rbl_data, hibp_data,
        )
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
