# role: `alertmanager` — K2 fix

> Решает **K2** из `docs/audit/v4.3_inspection.md`: alertmanager.yml содержал `chat_id: 0` (плейсхолдеры). Роль параметризует конфиг через шаблон Jinja2 и достаёт `chat_id`/`bot_token` из Ansible Vault.

## Что делает

1. `apt install prometheus-alertmanager` (если ещё не стоит; можно через Docker/binary — см. `alertmanager_install_mode`)
2. `/etc/alertmanager/tg_bot_token`  — из vault, mode 0600, owner `alertmanager`
3. `/etc/alertmanager/smtp_password` — из vault, mode 0600
4. `/etc/alertmanager/alertmanager.yml` — template'ится из `templates/alertmanager.yml.j2` (скопировано из `technical/0_Common/monitoring/alertmanager.yml` c `chat_id: {{ … }}` placeholder'ами)
5. `amtool check-config /etc/alertmanager/alertmanager.yml` в pre-task → fail-fast если конфиг невалиден
6. Handler reload alertmanager

## Переменные (`defaults/main.yml` — безопасные; секретные должны переопределяться из vault)

- `alertmanager_install_mode` (default `apt`; альтернативы: `docker`, `binary`)
- `alertmanager_tg_bot_token` (vault, required)
- `alertmanager_smtp_password` (vault, required)
- `alertmanager_tg_chat_id_general` (vault, required) — основной канал
- `alertmanager_tg_chat_id_p1`      (vault, required) — P1-oncall канал
- `alertmanager_tg_chat_id_backup`  (vault, required) — backup-сигналы
- `alertmanager_smtp_from`       (default `alerts@mspshield.ru`)
- `alertmanager_smtp_smarthost`  (default `smtp.yandex.ru:587`)
- `alertmanager_email_p3_to`     (default `alerts@mspshield.ru`)

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
# email_warning
```

Тест alert'а (вручную):
```bash
amtool alert add alertname=TestManual severity=P2 --alertmanager.url=http://localhost:9093
```
В Telegram-канал «general» должно упасть сообщение в течение 1 минуты.
