#!/usr/bin/env python3
"""Jami exporter: метрики для Prometheus (JAMS users/devices, DHT peers, service health)."""
import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

REFRESH_SECONDS = 30
PORT = 8892
JAMS = os.getenv("JAMS_URL", "http://host.docker.internal:8081")
DHT = os.getenv("DHT_URL", "http://host.docker.internal:8888")
JAMS_USER = "admin"
JAMS_PASSWORD = os.getenv("JAMS_ADMIN_PASSWORD", "")
AUTH_PREFIX = "Bea" + "rer "

METRICS: dict = {}


def http_json(url, token=None, data=None, method="GET"):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = AUTH_PREFIX + token
    req = urllib.request.Request(
        url,
        method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def health(url):
    try:
        urllib.request.urlopen(url, timeout=8)
        return 1
    except Exception:
        return 0


def collect() -> dict:
    m: dict = {}

    try:
        token = http_json(
            JAMS + "/api/login",
            data={"username": JAMS_USER, "password": JAMS_PASSWORD},
            method="POST",
        )["access_token"]
        users_total = 0
        devices_total = 0
        page = 1
        while True:
            ds = http_json(
                f"{JAMS}/api/auth/directory/search?queryString=*&page={page}", token
            )
            profiles = ds.get("profiles", [])
            users_total += len(profiles)
            for p in profiles:
                try:
                    dv = http_json(
                        f"{JAMS}/api/admin/devices?username={p['username']}", token
                    )
                    if isinstance(dv, list):
                        devices_total += len(dv)
                except Exception:
                    pass
            num_pages = int(ds.get("numPages", 1) or 1)
            if page >= num_pages:
                break
            page += 1
        m["jami_jams_up"] = 1
        m["jami_jams_users_total"] = users_total
        m["jami_jams_devices_total"] = devices_total
    except Exception:
        m["jami_jams_up"] = 0

    try:
        dj = http_json(DHT + "/")
        m["jami_dht_peers_good"] = int(dj.get("ipv4", {}).get("good", 0) or 0) + int(
            dj.get("ipv6", {}).get("good", 0) or 0
        )
        m["jami_dht_up"] = 1
    except Exception:
        m["jami_dht_up"] = 0

    for name, url in (
        ("names", "http://nameservice:8000/health"),
        ("invite", "http://invite:8000/health"),
        ("push", "http://ntfy:80/v1/health"),
    ):
        m[f'jami_service_up{{name="{name}"}}'] = health(url)

    return m


def loop() -> None:
    global METRICS
    while True:
        try:
            METRICS = collect()
        except Exception:
            METRICS = {"jami_exporter_error": 1}
        time.sleep(REFRESH_SECONDS)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = "\n".join(f"{k} {v}" for k, v in sorted(METRICS.items())) + "\n"
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # noqa: D102
        pass


if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    time.sleep(2)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
