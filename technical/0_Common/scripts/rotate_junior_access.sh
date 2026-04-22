#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# rotate_junior_access.sh — ротация/отзыв доступов junior'а.
# Запускается при:
#   • прохождении испытательного (повышение уровня)
#   • выходе человека (revoke all)
#   • plan-rotation раз в 6 мес (refresh keys)
#
# Usage:
#   rotate_junior_access.sh <junior_name> promote
#   rotate_junior_access.sh <junior_name> revoke
#   rotate_junior_access.sh <junior_name> rotate
# ─────────────────────────────────────────────────────────────
set -euo pipefail

NAME="${1:-}"
MODE="${2:-}"
if [[ -z "$NAME" || -z "$MODE" ]]; then
  echo "Usage: $0 <junior_name> promote|revoke|rotate" >&2
  exit 1
fi

LOG="/var/log/access_rotation/${NAME}-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

case "$MODE" in
  promote)
    log "promote $NAME: granting senior-level access"
    # 1. Vaultwarden collection membership — Ваши скрипты вызова bitwarden-cli.
    log "  TODO: bw org-collection-member update ${NAME} -> internal/infra Read-Write"
    # 2. Ansible sudo rights: добавить в группу 'msp-senior' в inventory group_vars.
    log "  TODO: update group_vars/all.yml: msp_senior_users += ['${NAME}']"
    # 3. SSH: keep current key, but extend to all hosts (new roles).
    log "  Re-run: ansible-playbook playbooks/site.yml --tags ssh_keys"
    # 4. Kaiten role promoted (UI action).
    log "  MANUAL: Kaiten → Workspace settings → role: Senior"
    ;;

  revoke)
    log "revoke $NAME: removing all access"
    # 1. SSH key removed from inventory -> ansible removes from ~/.ssh/authorized_keys
    log "  TODO: remove from group_vars/all.yml msp_users, then ansible-playbook playbooks/site.yml --tags ssh_keys"
    # 2. Vaultwarden: remove from organization
    log "  TODO: bw org-member remove ${NAME}"
    # 3. Kaiten: deactivate user
    log "  MANUAL: Kaiten → deactivate ${NAME}"
    # 4. Telegram groups: remove.
    log "  MANUAL: kick from ops / customers / internal TG groups"
    # 5. Ноутбук: схема возврата из docs/hiring/offer_and_ndca.md
    log "  MANUAL: laptop return / payment within 10 days"
    # 6. Rotate passwords this user had access to:
    log "  MANUAL: rotate shared credentials this user knew (Vaultwarden audit -> list)"
    ;;

  rotate)
    log "rotate $NAME: generate new SSH key, refresh VPN peer"
    # 1. Instruct user to generate new SSH key locally; collect public key.
    log "  Ask user: ssh-keygen -t ed25519 -f ~/.ssh/mspshield_ed25519_rotate"
    log "  Put public key into group_vars/users.yml:${NAME}_pubkey"
    log "  ansible-playbook playbooks/site.yml --tags ssh_keys"
    # 2. Regenerate WireGuard peer
    log "  /etc/wireguard/tenants/juniors/${NAME}.conf: tenant_add.sh override"
    # 3. Rotate Vaultwarden personal password (user does in UI; we just verify).
    log "  Ask user to rotate their master password in Vaultwarden"
    ;;

  *)
    echo "Unknown mode: $MODE" >&2
    exit 1
    ;;
esac

log "done ($MODE for $NAME)"
