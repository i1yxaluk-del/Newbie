#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# dr_drill.sh — quarterly DR drill for a single tenant.
# Verifies that the latest restic snapshot can be restored into a scratch dir.
# Usage: ./dr_drill.sh <tenant_name> [--full]
#   --full   do a full restore (not just single file). Requires disk space.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

TENANT="${1:-}"
MODE="${2:-smoke}"
if [[ -z "$TENANT" ]]; then
  echo "Usage: $0 <tenant_name> [--full]" >&2
  exit 1
fi

LOG_DIR="/var/log/dr_drill"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="${LOG_DIR}/${TENANT}-${STAMP}.log"
mkdir -p "$LOG_DIR"

ENV_FILE="/etc/restic/tenants/${TENANT}.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"

echo "=== DR drill: $TENANT · $MODE · $STAMP ===" | tee -a "$LOG"

# 1. Repo integrity
echo "[1/4] restic check" | tee -a "$LOG"
restic check --read-data-subset=3% 2>&1 | tee -a "$LOG"

# 2. Latest snapshot id
SNAP="$(restic snapshots --json | jq -r '.[-1].id')"
echo "[2/4] latest snapshot: $SNAP" | tee -a "$LOG"

# 3. Restore target
TMP_DIR="$(mktemp -d /tmp/dr_${TENANT}_XXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [[ "$MODE" == "--full" ]]; then
  echo "[3/4] full restore to $TMP_DIR" | tee -a "$LOG"
  restic restore "$SNAP" --target "$TMP_DIR" 2>&1 | tee -a "$LOG"
else
  # Smoke: restore first file from snapshot
  FIRST_FILE="$(restic ls "$SNAP" --json | jq -r '.[] | select(.type=="file") | .path' | head -1)"
  echo "[3/4] smoke restore: $FIRST_FILE" | tee -a "$LOG"
  restic restore "$SNAP" --target "$TMP_DIR" --include "$FIRST_FILE" 2>&1 | tee -a "$LOG"
fi

# 4. Verify restored files exist and not empty
echo "[4/4] verify" | tee -a "$LOG"
FOUND="$(find "$TMP_DIR" -type f -size +0 | wc -l)"
if [[ "$FOUND" -lt 1 ]]; then
  echo "FAIL: no non-empty files restored" | tee -a "$LOG"
  exit 2
fi
echo "OK: $FOUND files restored non-empty" | tee -a "$LOG"
echo "=== DR drill passed for $TENANT ===" | tee -a "$LOG"
