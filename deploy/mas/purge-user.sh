#!/usr/bin/env bash
# purge-user.sh <username> — полное удаление учётной записи: MAS + Synapse (освобождает логин).
# Вызывается админкой портала при «удалить». Необратимая служебная операция.
# После удаления живой записи в Synapse выполняется рестарт Synapse (сброс кэшей в памяти).
set -u
U="${1:-}"
DOMAIN="m.msp-claude.online"
if ! printf '%s' "$U" | grep -Eq '^[a-z0-9][a-z0-9._-]{1,31}$'; then
  echo "ERR_BAD_USERNAME"; exit 2
fi
MXID="@${U}:${DOMAIN}"

MAS_OUT=$(sudo docker exec -i msp-mas-db psql -U mas -d mas -v ON_ERROR_STOP=1 -1 -q -v u="$U" <<'SQL' 2>&1
\set ON_ERROR_STOP on
CREATE TEMP TABLE _u ON COMMIT DROP AS SELECT user_id FROM users WHERE username = :'u';
DELETE FROM compat_refresh_tokens WHERE compat_session_id IN (SELECT compat_session_id FROM compat_sessions WHERE user_id IN (SELECT user_id FROM _u));
DELETE FROM compat_access_tokens WHERE compat_session_id IN (SELECT compat_session_id FROM compat_sessions WHERE user_id IN (SELECT user_id FROM _u));
DELETE FROM compat_sessions WHERE user_id IN (SELECT user_id FROM _u);
DELETE FROM oauth2_refresh_tokens WHERE oauth2_session_id IN (SELECT oauth2_session_id FROM oauth2_sessions WHERE user_id IN (SELECT user_id FROM _u)) OR oauth2_access_token_id IN (SELECT oauth2_access_token_id FROM oauth2_access_tokens WHERE oauth2_session_id IN (SELECT oauth2_session_id FROM oauth2_sessions WHERE user_id IN (SELECT user_id FROM _u)));
DELETE FROM oauth2_access_tokens WHERE oauth2_session_id IN (SELECT oauth2_session_id FROM oauth2_sessions WHERE user_id IN (SELECT user_id FROM _u));
DELETE FROM oauth2_authorization_grants WHERE oauth2_session_id IN (SELECT oauth2_session_id FROM oauth2_sessions WHERE user_id IN (SELECT user_id FROM _u)) OR user_session_id IN (SELECT user_session_id FROM user_sessions WHERE user_id IN (SELECT user_id FROM _u));
DELETE FROM oauth2_device_code_grant WHERE oauth2_session_id IN (SELECT oauth2_session_id FROM oauth2_sessions WHERE user_id IN (SELECT user_id FROM _u)) OR user_session_id IN (SELECT user_session_id FROM user_sessions WHERE user_id IN (SELECT user_id FROM _u));
DELETE FROM upstream_oauth_authorization_sessions WHERE user_session_id IN (SELECT user_session_id FROM user_sessions WHERE user_id IN (SELECT user_id FROM _u)) OR upstream_oauth_link_id IN (SELECT upstream_oauth_link_id FROM upstream_oauth_links WHERE user_id IN (SELECT user_id FROM _u));
DELETE FROM user_session_authentications WHERE user_session_id IN (SELECT user_session_id FROM user_sessions WHERE user_id IN (SELECT user_id FROM _u));
DELETE FROM user_email_authentications WHERE user_session_id IN (SELECT user_session_id FROM user_sessions WHERE user_id IN (SELECT user_id FROM _u));
DELETE FROM oauth2_sessions WHERE user_id IN (SELECT user_id FROM _u);
DELETE FROM user_sessions WHERE user_id IN (SELECT user_id FROM _u);
DELETE FROM personal_access_tokens WHERE personal_session_id IN (SELECT personal_session_id FROM personal_sessions WHERE owner_user_id IN (SELECT user_id FROM _u) OR actor_user_id IN (SELECT user_id FROM _u));
DELETE FROM personal_sessions WHERE owner_user_id IN (SELECT user_id FROM _u) OR actor_user_id IN (SELECT user_id FROM _u);
DELETE FROM upstream_oauth_links WHERE user_id IN (SELECT user_id FROM _u);
DELETE FROM user_passwords WHERE user_id IN (SELECT user_id FROM _u);
DELETE FROM users WHERE user_id IN (SELECT user_id FROM _u);
SELECT 'PURGE_LEFT=' || count(*) FROM users WHERE username = :'u';
SQL
)
if ! printf '%s' "$MAS_OUT" | grep -q 'PURGE_LEFT=0'; then
  echo "PURGE_FAIL_MAS: $(printf '%s' "$MAS_OUT" | tail -2)"; exit 1
fi

SYEXIST=$(sudo docker exec -i msp-synapse-db psql -U synapse -d synapse -t -A -c "SELECT count(*) FROM users WHERE name = '${MXID}';" 2>/dev/null)
SY_OUT=$(sudo docker exec -i msp-synapse-db psql -U synapse -d synapse -v ON_ERROR_STOP=1 -1 -q -v u="$MXID" <<'SQL2' 2>&1
\set ON_ERROR_STOP on
CREATE TEMP TABLE _su ON COMMIT DROP AS SELECT :'u'::text AS name, regexp_replace(:'u'::text, '^@([^:]+):.*$', '\1') AS localpart;
DO $do$
DECLARE
  t text;
  lst text[] := ARRAY['e2e_keys','e2e_cross_signing_keys','e2e_cross_signing_signatures','e2e_room_keys','devices','profiles','pushers','user_threepids','account_data','room_account_data','receipts','refresh_tokens','access_tokens','login_tokens','ratelimit_override','users_to_send_full_presence_to','thread_subscriptions','per_user_experimental_features','user_directory','user_directory_search','blocked_room_ids'];
BEGIN
  FOREACH t IN ARRAY lst LOOP
    IF EXISTS (SELECT 1 FROM information_schema.columns c WHERE c.table_name = t AND c.column_name = 'user_id') THEN
      EXECUTE format('DELETE FROM %I WHERE user_id IN (SELECT name FROM _su) OR user_id IN (SELECT localpart FROM _su)', t);
    END IF;
  END LOOP;
END
$do$;
DELETE FROM scheduled_tasks WHERE resource_id IN (SELECT name FROM _su);
DELETE FROM worker_locks WHERE lock_key IN (SELECT name FROM _su);
DELETE FROM users WHERE name IN (SELECT name FROM _su);
SELECT 'SYNAPSE_LEFT=' || count(*) FROM users WHERE name IN (SELECT name FROM _su);
SQL2
)
if ! printf '%s' "$SY_OUT" | grep -q 'SYNAPSE_LEFT=0'; then
  echo "PURGE_FAIL_SYNAPSE: $(printf '%s' "$SY_OUT" | tail -3)"; exit 1
fi

if [ "${SYEXIST:-0}" != "0" ]; then
  echo "SYNAPSE_RESTARTED (cache reset)"
  sudo docker restart msp-synapse >/dev/null 2>&1
  for i in $(seq 1 40); do
    S=$(sudo docker inspect msp-synapse --format '{{.State.Health.Status}}' 2>/dev/null)
    [ "$S" = "healthy" ] && break
    sleep 2
  done
fi
echo "PURGE_OK"
exit 0
