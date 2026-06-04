from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8950653616:AAGn3UrlAxD3sWP5hmnKpB6EvT2kiCxof_I")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1004230593984")
PORT = int(os.environ.get("TELEGRAM_WEBHOOK_PORT", "9119"))
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

EMOJI = {"P1": "🔴", "P2": "🟡", "P3": "🔵"}
STATUS_EMOJI = {"firing": "🔥", "resolved": "✅"}


def format_message(data):
    status = data.get("status", "firing")
    alerts = data.get("alerts", [])
    se = STATUS_EMOJI.get(status, "")
    lines = [f"<b>{se} MSPShield · {status.upper()}</b>\n"]

    for a in alerts:
        labels = a.get("labels", {})
        annotations = a.get("annotations", {})
        severity = labels.get("severity", "?")
        emoji = EMOJI.get(severity, "⚪")
        summary = annotations.get("summary", labels.get("alertname", "Alert"))
        host = annotations.get("host", "")
        lines.append(f"{emoji} <b>[{severity}]</b> {summary}")
        if host:
            lines.append(f"   host: <code>{host}</code>")
        runbook = annotations.get("runbook", "")
        if runbook:
            lines.append(f'   <a href="{runbook}">runbook</a>')
        lines.append("")

    external_url = data.get("externalURL", "")
    if external_url:
        lines.append(f'<a href="{external_url}">Grafana</a>')
    return "\n".join(lines)


def send_telegram(text):
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        text = format_message(data)
        ok = send_telegram(text)
        self.send_response(200 if ok else 502)
        self.end_headers()
        self.wfile.write(b"ok" if ok else b"error")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"MSPShield Telegram webhook proxy")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Telegram webhook proxy on :{PORT} → chat {CHAT_ID}")
    server.serve_forever()
