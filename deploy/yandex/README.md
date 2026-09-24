# Yandex Cloud production deployment

Канонический сценарий для текущего пилота: одна VM, Caddy, Docker Compose, monitoring stack и отдельные encrypted backups.

## Порядок

1. Создать VM, static IP и Security Group.
2. Разместить репозиторий в `/opt/msp/Newbie`.
3. Создать новые env; не копировать старые cloud credentials.
4. Выполнить preflight.
5. Запустить application stack и monitoring.
6. Проверить health, MAX session и Postbox email.
7. Выполнить тестовый P1.
8. Создать backup и clean-room restore evidence.
9. Только затем переключать DNS.

```bash
cd /opt/msp/Newbie
bash scripts/deployment/preflight.sh --fix
cd deploy/yandex && sudo docker compose up -d --build
cd monitoring && sudo docker compose up -d --build
```

## Обязательные env

- `backend/.env`: `ADMIN_TOKEN`, `MONGO_URL`, `DB_NAME`;
- `deploy/yandex/.env`: `VAULTWARDEN_ADMIN_TOKEN`;
- `monitoring/.env`: `GRAFANA_ADMIN_PASSWORD`, `ALERTMANAGER_WEBHOOK_TOKEN`, `SMTP_AUTH_USER`, `SMTP_AUTH_PASSWORD`, `MAX_PHONE`, `MAX_CHAT_ID`.

`SMTP_AUTH_USER` — ID Postbox API key, `SMTP_AUTH_PASSWORD` — secret ключа. Service-account ID вместо API-key ID даст SMTP 535.

## Проверки

```bash
curl -fsS http://127.0.0.1:8001/api/health
curl -fsS http://127.0.0.1:9090/-/healthy
curl -fsS http://127.0.0.1:9093/-/healthy
curl -fsS http://127.0.0.1:9095/health
sudo docker exec msp-max-alerter python -m max_alerter.auth
```

## Уроки и troubleshooting

- Матрица внедрённых контролей: [`../../docs/deployment/DEPLOYMENT_LESSONS.md`](../../docs/deployment/DEPLOYMENT_LESSONS.md).
- MAX: [`../../docs/MAX_SETUP.md`](../../docs/MAX_SETUP.md).
- Migration: [`../../migration/README.md`](../../migration/README.md).
- DR: [`../../docs/deployment/disaster_recovery.md`](../../docs/deployment/disaster_recovery.md).

Исторические cloud IDs, IP и ключи не являются документацией и не должны храниться в Git.
