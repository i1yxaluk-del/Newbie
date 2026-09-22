#!/usr/bin/env bash
# Non-invasive external perimeter check. Run from a host outside the production VPC.
set -euo pipefail
HOST="${1:-msp-claude.online}"
OUT="${2:-external-scan-$(date +%Y%m%d-%H%M%S).txt}"
{
  echo "host=$HOST time=$(date -Iseconds)"
  echo "== DNS =="; getent ahosts "$HOST" || true
  echo "== HTTPS headers =="; curl -fsSI --max-time 15 "https://$HOST/" || true
  echo "== Certificate =="; echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null | openssl x509 -noout -subject -issuer -dates || true
  echo "== Expected public ports =="
  if command -v nmap >/dev/null; then
    nmap -Pn -sT --reason -p 22,25,80,443,465,587,8001,8080,8180,27017 "$HOST"
  else
    for port in 22 25 80 443 465 587 8001 8080 8180 27017; do
      timeout 3 bash -c "</dev/tcp/$HOST/$port" 2>/dev/null && echo "$port open" || echo "$port closed/filtered"
    done
  fi
  echo "PASS criteria: 80/443 expected; 8001/8080/8180/27017 must be closed. Mail ports only if the optional mail profile is intentionally enabled."
} | tee "$OUT"
