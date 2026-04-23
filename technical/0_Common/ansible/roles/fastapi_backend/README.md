# role: `fastapi_backend`

> Разворачивает FastAPI бэкенд лендинга (`backend/server.py`) на landing-VM под systemd + uvicorn.

## Что делает

1. `python3.11-venv` + user `mspshield`
2. `git clone`/pull репо → `/opt/mspshield`
3. `pip install -r backend/requirements.txt` в venv
4. `/etc/mspshield/backend.env` ← из Vaultwarden (локально — копируется Ansible Vault)
5. systemd unit `mspshield-backend.service` (uvicorn на 127.0.0.1:8001)
6. enable + start; `ExecStartPre=python -c "import motor.motor_asyncio"` как smoke

## Переменные

- `fastapi_repo_url` (default: git@github.com:i1yxaluk-del/Newbie.git)
- `fastapi_repo_ref` (default: main)
- `fastapi_install_dir` (default: /opt/mspshield)
- `fastapi_system_user` (default: mspshield)
- `fastapi_env_content` (required, **secret**) — содержимое `.env` (вытаскивается из Ansible Vault)
- `fastapi_port` (default: 8001)

## Секреты

Все ключи (`ADMIN_TOKEN`, `TG_BOT_TOKEN`, `SMARTCAPTCHA_SERVER_KEY`, и др.) держим в `group_vars/landing/vault.yml` (ansible-vault). См. `docs/deployment/secrets_management.md`.

## Smoke

После apply: `curl -s http://127.0.0.1:8001/api/` должен вернуть `{"service":"MSPShield API","version":"4.2.0"}`.
