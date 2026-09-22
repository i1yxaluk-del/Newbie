#!/usr/bin/env bash
# Restore drill with measured RTO/RPO. Requires /etc/restic/tenants/<tenant>.env.
set -euo pipefail

TENANT="${1:-}"
MODE="${2:-smoke}"
[[ -n "$TENANT" ]] || { echo "Usage: $0 <tenant_name> [--full]" >&2; exit 1; }

LOG_DIR="/var/log/dr_drill"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="${LOG_DIR}/${TENANT}-${STAMP}.log"
RESULT="${LOG_DIR}/${TENANT}-${STAMP}.json"
mkdir -p "$LOG_DIR"
ENV_FILE="/etc/restic/tenants/${TENANT}.env"
[[ -f "$ENV_FILE" ]] || { echo "Env file not found: $ENV_FILE" >&2; exit 1; }
# shellcheck source=/dev/null
source "$ENV_FILE"

START_EPOCH="$(date +%s)"
echo "=== DR drill: $TENANT · $MODE · $STAMP ===" | tee -a "$LOG"
restic check --read-data-subset=3% 2>&1 | tee -a "$LOG"
SNAP_JSON="$(restic snapshots --json | jq '.[-1]')"
SNAP="$(jq -r '.id' <<<"$SNAP_JSON")"
SNAP_TIME="$(jq -r '.time' <<<"$SNAP_JSON")"
SNAP_EPOCH="$(date -d "$SNAP_TIME" +%s)"
RPO_SECONDS="$((START_EPOCH - SNAP_EPOCH))"

TMP_DIR="$(mktemp -d /tmp/dr_${TENANT}_XXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
if [[ "$MODE" == "--full" ]]; then
  restic restore "$SNAP" --target "$TMP_DIR" 2>&1 | tee -a "$LOG"
else
  FIRST_FILE="$(restic ls "$SNAP" --json | jq -r '.[] | select(.type=="file") | .path' | head -1)"
  [[ -n "$FIRST_FILE" ]] || { echo "FAIL: snapshot has no files" | tee -a "$LOG"; exit 2; }
  restic restore "$SNAP" --target "$TMP_DIR" --include "$FIRST_FILE" 2>&1 | tee -a "$LOG"
fi
FOUND="$(find "$TMP_DIR" -type f -size +0 | wc -l)"
[[ "$FOUND" -ge 1 ]] || { echo "FAIL: no non-empty files restored" | tee -a "$LOG"; exit 2; }
END_EPOCH="$(date +%s)"
RTO_SECONDS="$((END_EPOCH - START_EPOCH))"
BYTES="$(du -sb "$TMP_DIR" | cut -f1)"

jq -n \
  --arg tenant "$TENANT" --arg mode "$MODE" --arg snapshot "$SNAP" \
  --arg snapshot_time "$SNAP_TIME" --argjson rto "$RTO_SECONDS" \
  --argjson rpo "$RPO_SECONDS" --argjson files "$FOUND" --argjson bytes "$BYTES" \
  '{status:"passed",tenant:$tenant,mode:$mode,snapshot:$snapshot,snapshot_time:$snapshot_time,rto_seconds:$rto,rpo_seconds:$rpo,restored_files:$files,restored_bytes:$bytes}' \
  | tee "$RESULT"
echo "PASS: RTO=${RTO_SECONDS}s RPO=${RPO_SECONDS}s evidence=$RESULT" | tee -a "$LOG"
