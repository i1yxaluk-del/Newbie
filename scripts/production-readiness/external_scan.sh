#!/usr/bin/env bash
# Non-invasive external perimeter check. Run from a host outside production VPC.
set -euo pipefail
HOST="${1:-msp-claude.online}"
OUT="${2:-external-scan-$(date +%Y%m%d-%H%M%S).txt}"
{
  echo "host=$HOST time=$(date -Iseconds)"
  echo "== DNS =="; getent ahosts "$HOST" || true
  echo "== HTTPS headers =="; curl -fsSI --max-time 15 "https://$HOST/" || true
  echo "== Certificate =="; echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null | openssl x509 -noout -subject -issuer -dates || true
  echo "== TCP ports =="
  for port in 22 25 80 443 465 587 8001 8080 8180 27017; do
    timeout 3 bash -c "</dev/tcp/$HOST/$port" 2>/dev/null && echo "$port open" || echo "$port closed/filtered"
  done
  echo "PASS criteria: 80/443 expected; 8001/8080/8180/27017 must be closed. Mail ports only if explicitly enabled."
} | tee "$OUT"

if grep -Eq '^(8001|8080|8180|27017) open$' "$OUT"; then
  echo "FAIL: a restricted service is externally reachable" | tee -a "$OUT"
  exit 2
fi
if ! grep -Eq '^443 open$' "$OUT"; then
  echo "FAIL: HTTPS is not externally reachable" | tee -a "$OUT"
  exit 3
fi
echo "PASS: restricted application/database ports are closed" | tee -a "$OUT"
