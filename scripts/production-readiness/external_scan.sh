#!/usr/bin/env bash
# Назначение: неинвазивно проверить внешний периметр production с внешнего хоста.
# Где запускать: GitHub Actions или машина вне production VPC.
# Входы: домен и необязательный путь отчёта.
# Побочные эффекты: только создаёт текстовый отчёт; конфигурацию не меняет.
# Успех: HTTPS доступен, внутренние порты закрыты.
# Откат: не требуется.
set -euo pipefail

HOST="${1:-msp-claude.online}"
OUT="${2:-external-scan-$(date +%Y%m%d-%H%M%S).txt}"

{
  echo "host=$HOST time=$(date -Iseconds)"
  echo "== DNS =="; getent ahosts "$HOST" || true
  echo "== HTTPS headers =="; curl -fsSI --max-time 15 "https://$HOST/" || true
  echo "== Certificate =="; echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null | openssl x509 -noout -subject -issuer -dates || true
  echo "== TCP ports =="
  # Набор содержит публичные web/mail-порты и внутренние порты, которые нельзя публиковать.
  for port in 22 25 80 443 465 587 8001 8080 8180 27017; do
    timeout 3 bash -c "</dev/tcp/$HOST/$port" 2>/dev/null && echo "$port open" || echo "$port closed/filtered"
  done
  echo "Критерий: 443 открыт; 8001/8080/8180/27017 закрыты. Mail-порты — только при явном включении."
} | tee "$OUT"

if grep -Eq '^(8001|8080|8180|27017) open$' "$OUT"; then
  echo "FAIL: внутренний сервис доступен из интернета" | tee -a "$OUT"
  exit 2
fi
if ! grep -Eq '^443 open$' "$OUT"; then
  echo "FAIL: HTTPS недоступен из интернета" | tee -a "$OUT"
  exit 3
fi
echo "PASS: HTTPS доступен, внутренние порты закрыты" | tee -a "$OUT"
