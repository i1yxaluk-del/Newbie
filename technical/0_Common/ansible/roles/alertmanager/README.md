# role: `alertmanager` — K2 fix

> Решает **K2** из `docs/audit/v4.3_inspection.md`: alertmanager.yml содержал `chat_id: 0` (плейсхолдеры). Роль параметризует конфиг через шаблон Jinja2 и достаёт `chat_id`/`bot_token` из Ansible Vault.
>
> С v4.6 поддержаны **два канала**: Telegram (напрямую из Alertmanager) и MAX (через webhook на backend `/api/alerts/alertmanager`, см. [`docs/MAX_SETUP.md` §10](../../../../../docs/MAX_SETUP.md)).

## Что делает

1. `apt install prometheus-alertmanager` (если ещё не стоит; можно через Docker/binary — см. `alertmanager_install_mode`)
2. `/etc/alertmanager/tg_bot_token`  — из vault, mode 0600, owner `alertmanager`
3. `/etc/alertmanager/max_webhook_token` — Bearer-токен для backend `/api/alerts/alertmanager` (соотв. `ALERTMANAGER_WEBHOOK_TOKEN` в `backend/.env`), mode 0600
4. `/etc/alertmanager/smtp_password` — из vault, mode 0600
5. `/etc/alertmanager/alertmanager.yml` — template'ится из `templates/alertmanager.yml.j2` (скопировано из `technical/0_Common/monitoring/alertmanager.yml` c `chat_id: {{ … }}` placeholder'ами; содержит receivers `telegram*` и `msp-max-tg` — первый шлёт напрямую в Telegram, второй через backend в MAX+Telegram fan-out)
6. `amtool check-config /etc/alertmanager/alertmanager.yml` в pre-task → fail-fast если конфиг невалиден
7. Handler reload alertmanager

## Переменные (`defaults/main.yml` — безопасные; секретные должны переопределяться из vault)

- `alertmanager_install_mode` (default `apt`; альтернативы: `docker`, `binary`)
- `alertmanager_tg_bot_token` (vault, required если включён Telegram-канал)
- `alertmanager_tg_chat_id_general` (vault, required если TG) — основной канал
- `alertmanager_tg_chat_id_p1`      (vault, required если TG) — P1-oncall канал
- `alertmanager_tg_chat_id_backup`  (vault, required если TG) — backup-сигналы
- `alertmanager_max_webhook_url`    (default `https://msp-oblako.ru/api/alerts/alertmanager`) — endpoint backend’а
- `alertmanager_max_webhook_token`  (vault, required если включён MAX-канал) — Bearer-токен для вызова backend (`ALERTMANAGER_WEBHOOK_TOKEN`)
- `alertmanager_smtp_password` (vault, required)
- `alertmanager_smtp_from`       (default `alerts@mspshield.ru`)
- `alertmanager_smtp_smarthost`  (default `smtp.yandex.ru:587`)
- `alertmanager_email_p3_to`     (default `alerts@mspshield.ru`)

> Выбор каналов делается в `backend/.env` через `ALERT_CHANNELS=max,telegram` (или один из). Alertmanager шлёт всегда на backend — backend решает куда fan-out‘ить.

## Где вариативные chat_id лежат в vault

`group_vars/landing/vault.yml` — зашифровано `ansible-vault encrypt`. Пример структуры в `group_vars/landing/vault.example.yml` (в plaintext, без реальных значений).

## Smoke после apply

```bash
curl -s http://localhost:9093/-/healthy
# OK
curl -s http://localhost:9093/api/v2/receivers | jq '.[].name'
# telegram
# telegram_p1
# telegram_backup
# msp-max-tg
# email_warning
```

Тест alert'а (вручную):
```bash
amtool alert add alertname=TestManual severity=P2 --alertmanager.url=http://localhost:9093
```
В Telegram-канале «general» и/или в MAX (в зависимости от `ALERT_CHANNELS` в backend) должно упасть сообщение в течение 1 минуты. Для Wazuh-сценария формат сообщения: `🔴 P1 · TestManual · <env>`.
