# Troubleshooting развёртывания

Типовые проблемы, с которыми сталкиваешься при первом развёртывании и онбординге клиентов.

## Локальная разработка

### docker compose up: `Error response from daemon: Ports are not available`

Порт уже занят другим процессом.

```bash
# Найти, кто занял:
sudo ss -ltnp | grep -E ":(3000|8001|27017)"
# kill или изменить порт в deploy/docker-compose.yml
```

### Frontend собирается и падает с `ENOSPC`

Закончилось место на диске или inotify-лимиты.

```bash
# Очистить docker:
docker system prune -af --volumes
# Поднять inotify-лимит:
sudo sysctl fs.inotify.max_user_watches=524288
```

### MongoDB пишет в лог `WiredTiger.lock`

Предыдущий контейнер упал, лок-файл остался.

```bash
cd deploy
docker compose down
docker volume rm deploy_mongo_data  # ВНИМАНИЕ: удалит данные
docker compose up -d
```

### Telegram bot не отвечает, в логах backend нет ошибок

Проверить:

1. `TG_BOT_TOKEN` корректный (попробовать `curl https://api.telegram.org/bot<TOKEN>/getMe`).
2. Бот добавлен в нужную группу, имеет права писать.
3. `TG_CHAT_ID` — с минусом (для групп) или без (для личных чатов).

### MAX bot не отвечает / webhook не приходит

Проверить:

1. `MAX_BOT_TOKEN` корректный — `curl https://botapi.max.ru/me?access_token=$MAX_BOT_TOKEN` должен вернуть профиль бота.
2. Webhook зарегистрирован: `curl https://botapi.max.ru/subscriptions?access_token=$MAX_BOT_TOKEN` — должен быть список с вашим URL.
3. URL обязательно `https://` с **валидным** TLS (не self-signed, не Let's Encrypt staging) — MAX отвергает невалидные сертификаты.
4. `MAX_WEBHOOK_SECRET` совпадает между `backend/.env` и тем, что отправили в `POST /subscriptions`.
5. `journalctl -u mspshield-backend | grep max` — backend пишет, что пришёл webhook с правильным `X-Max-Bot-Api-Secret`.

Перезарегистрировать webhook:

```bash
cd /opt/mspshield && python scripts/max_setup_webhook.py
```

Подробнее: [`docs/MAX_SETUP.md` §6 «Типичные ошибки»](../MAX_SETUP.md).

### Alertmanager шлёт алёрты, но в MAX ничего не приходит

```bash
# 1. backend получает webhook?
sudo journalctl -u mspshield-backend | grep alertmanager
# 2. ALERT_CHANNELS включает max?
grep ALERT_CHANNELS /etc/mspshield/backend.env
# 3. Bearer-токен совпадает?
diff <(grep ALERTMANAGER_WEBHOOK_TOKEN /etc/mspshield/backend.env | cut -d= -f2) \
     <(cat /etc/alertmanager/max_webhook_token)
# 4. Тест:
curl -X POST -H "Authorization: Bearer $(cat /etc/alertmanager/max_webhook_token)" \
  -H "Content-Type: application/json" \
  -d '{"alerts":[{"status":"firing","labels":{"alertname":"TestMAX","severity":"warning"}}]}' \
  https://msp-claude.online/api/alerts/alertmanager
```

## Terraform

### `Error: Error creating instance: quota for instance-cpu exceeded`

Бесплатная квота Yandex Cloud — 2 vCPU. Надо либо:

1. Подать заявку в поддержке на увеличение (бесплатно, 1–2 дня).
2. Временно уменьшить `resources.cores = 2` до `1` (для dev/staging).

### `Error: failed to read state file`

Проблема с S3-backend. Проверить:

```bash
# Ключи доступа:
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
# Бакет существует:
yc storage bucket get mspshield-tfstate
# Если нет — пересоздать.
```

### `terraform destroy` не удаляет bucket с объектами

```bash
# Сначала очистить:
yc storage s3api delete-objects --bucket mspshield-backups-new ...
# Потом destroy.
```

## Ansible

### `UNREACHABLE! => Failed to connect to the host via ssh`

1. Проверить `$BASTION_PUBLIC_IP` — выставлен?
2. SSH на bastion работает из твоей машины? (`ssh ubuntu@<bastion_ip>`).
3. SSH с bastion на тенант работает? (На bastion: `ssh ubuntu@10.20.10.11`).
4. AmneziaWG up на обеих сторонах?

```bash
# На bastion:
sudo awg show
# peer должен быть с latest handshake < 3 мин назад
```

### `Privilege escalation failed`

Пользователь `ubuntu` не в sudoers или требует пароль.

```bash
# На клиентском хосте (через bastion):
sudo visudo
# Добавить:
# ubuntu ALL=(ALL) NOPASSWD:ALL
```

### `"msg": "Failed to find required executable \"python3\""`

На хосте нет Python. Ansible < 2.14 это терпит, новее — нет.

```bash
# На хосте:
sudo apt install -y python3
# Или в инвентаре:
# ansible_python_interpreter: /usr/bin/python3.11
```

## AmneziaWG

### Peer подключается, но пинг не проходит

```bash
# На обеих сторонах проверить:
sudo awg show
# В AllowedIPs должны быть подсети противоположной стороны.
# Например, на клиенте AllowedIPs = 10.9.0.0/24, 10.20.0.0/16.

# На bastion:
sudo iptables -t nat -L POSTROUTING -v
# Должен быть MASQUERADE для 10.20.x.x → eth0 (если нужно, чтобы клиенты ходили в интернет через bastion).

# IP forwarding включен?
sudo sysctl net.ipv4.ip_forward
# Должно быть 1. Если 0:
# sudo sysctl -w net.ipv4.ip_forward=1
# echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-awg-forward.conf
```

### Handshake постоянно пропадает (возможно РКН/DPI в регионе клиента)

AmneziaWG специально против РКН-DPI, но работает только при ИДЕНТИЧНЫХ
параметрах обфускации на обеих сторонах:

```bash
# Сравнить на bastion и клиенте:
sudo grep -E '^(Jc|Jmin|Jmax|S1|S2|H1|H2|H3|H4) ' /etc/amnezia/amneziawg/awg0.conf
# Все 9 чисел ДОЛЖНЫ совпадать. При любом расхождении handshake не пройдёт.
# Регенерировать клиент-конфиг через tenant_add.sh — он
# автоматически читает эти параметры с сервера.
```

### AmneziaWG не поднимается после reboot или kernel-update

```bash
sudo systemctl status awg-quick@awg0
# Смотреть journalctl:
sudo journalctl -u awg-quick@awg0 -n 50
# Часто: неправильные права на ключи.
sudo chmod 600 /etc/amnezia/amneziawg/*.key
sudo systemctl restart awg-quick@awg0

# DKMS-модуль не пересобрался после обновления ядра?
lsmod | grep amneziawg
# Пусто → sudo apt-get install --reinstall amneziawg-dkms
```

## SSL / certbot

### `Failed authorization procedure: ... urn:acme:error:connection`

Let's Encrypt не может достучаться до `https://msp-claude.online/.well-known/acme-challenge/`. Проверить:

1. nginx работает и отдаёт `/.well-known/` (смотреть `deploy/nginx/mspshield.conf`).
2. DNS A-запись правильная.
3. Фаервол пропускает 80.

```bash
curl https://msp-claude.online/.well-known/acme-challenge/test
# Должен быть 404 от nginx, а не connection refused.
```

### `Too many requests - IP: rate limit`

Let's Encrypt ratelimit — 5 неудачных попыток в час. Ждать час или:

```bash
# Использовать staging env для дебага:
sudo certbot --staging --nginx -d msp-claude.online
```

## Backend

### `500 Internal Server Error` на `/api/leads` POST

```bash
# На landing-VM:
sudo journalctl -u mspshield-backend -n 100
# Типовые:
# - "AttributeError" → код после переезда, пересобрать.
# - "ServerSelectionTimeoutError" → MongoDB недоступна.
# - "ValidationError" → frontend шлёт несовместимый payload.
```

### `/metrics` возвращает 404

`prometheus_client` не установлен. Проверить `backend/requirements.txt`:

```
prometheus_client>=0.17.0
```

Переустановить:

```bash
cd /opt/mspshield/backend
sudo -u mspshield pip install -r requirements.txt
sudo systemctl restart mspshield-backend
```

### Rate-limit срабатывает для легитимного пользователя

Поднять порог в `backend/.env`:

```
RATE_LIMIT_PER_MIN=30
RATE_LIMIT_WINDOW_SEC=60
```

Либо (лучше для атак) — включить SmartCaptcha вместо поднятия limit'а.

## MongoDB

### `MongoServerSelectionError: connection refused`

MongoDB не запущен или слушает не там.

```bash
sudo systemctl status mongodb
sudo ss -ltn | grep 27017
# Должно быть 127.0.0.1:27017

# В /etc/mongod.conf:
# bindIp: 127.0.0.1
```

### Размер базы растёт — что делать

Лиды за 2 года — около 100–500 МБ. Пока не беспокоимся. Если > 5 ГБ:

```bash
# Архив старых заявок в отдельную коллекцию:
mongo mspshield --eval 'db.leads.aggregate([{$match:{created_at:{$lt:ISODate("2024-01-01")}}},{$out:"leads_archive_2023"}])'
# Удалить оригиналы:
mongo mspshield --eval 'db.leads.deleteMany({created_at:{$lt:ISODate("2024-01-01")}})'
```

## Prometheus / Alertmanager

### Таргет в Prometheus `DOWN`, но сам хост жив

```bash
# Проверить node_exporter на целевом хосте:
ssh ubuntu@acme-srv01
sudo systemctl status prometheus-node-exporter
curl http://localhost:9100/metrics | head

# Проверить, что Prometheus может дотянуться:
# На landing-VM:
curl http://10.20.10.11:9100/metrics
# Если timeout — проблема с WireGuard, не Prometheus.
```

### Алёрт не уходит в Telegram

1. Проверить routing в `alertmanager.yml` (матчинг лейблов).
2. `curl http://localhost:9093/api/v2/alerts` — алёрт вообще в очереди?
3. `journalctl -u alertmanager -n 100` — ошибки от Telegram API?

Частая ошибка: `chat_id` с минусом для каналов/групп, без минуса для лички. Проверить.

## Общее: «не знаю что сломано»

Универсальный health-check:

```bash
bash technical/0_Common/scripts/verify_all.sh
# Должен пройти все проверки.
```

Если что-то красное — проблема там, куда указал скрипт.

## Эскалация

Если больше часа не продвигаешься и это production:

1. Написать вопрос в Cognition AI Devin.
2. Написать в профильные TG-чаты (`@devops_ru`, `@yandex_cloud`).
3. Yandex Cloud Support (только для плат. аккаунтов).

Если это не production (dev, staging) — отложить, завтра свежими глазами.
