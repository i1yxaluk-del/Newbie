# Онбординг клиента (тенанта)

Цель: за 1–7 дней развернуть клиенту его стек (Bronze/Silver/Gold), подключить его к AmneziaWG (UDP/443, обфускация против РКН-DPI), запустить бэкапы и мониторинг, начать выполнение SLA.

**Предпосылки:**

- Лендинг уже развернут ([`landing_production.md`](landing_production.md)).
- Bastion с AmneziaWG работает (UDP/443).
- Контракт с клиентом подписан (НПД).
- Получены реквизиты клиента, описание инфры, админ-доступы.

**Время:**

- Bronze: 4–8 часов чистого времени, растягивается на 3–7 дней (зависит от клиента).
- Silver: 1–2 дня.
- Gold: 2–4 дня (+ выездной аудит).

**Связанные документы:**

- [`../onboarding/pre_onboarding_checklist.md`](../onboarding/pre_onboarding_checklist.md) — что собрать ДО старта.
- [`../onboarding/day_1_7_runbook.md`](../onboarding/day_1_7_runbook.md) — день-за-днём.
- [`../onboarding/welcome_package.md`](../onboarding/welcome_package.md) — что отдать клиенту.

---

## Шаг 0. Pre-onboarding чек-лист

**До начала технических работ** убедись, что собрано:

- [ ] Подписан контракт (НПД-форма, см. `contracts/contract_bronze.html` или аналогичный для тарифа).
- [ ] Выставлен счёт, получена оплата **первого месяца** (не начинаем работы без предоплаты).
- [ ] Получены реквизиты: название организации, ИНН, ФИО директора, email для welcome-package.
- [ ] Клиент заполнил мини-анкету инфры (кол-во серверов, сайтов, почта, AD/без AD, версия ОС).
- [ ] Получен SSH-доступ к клиентским хостам (отдельный пользователь `mspadmin` с sudo через `ansible`).
- [ ] Согласована первая patch-window (день недели + время + часовой пояс).

Подробнее: [`../onboarding/pre_onboarding_checklist.md`](../onboarding/pre_onboarding_checklist.md).

---

## Шаг 1. Создать tenant-подсеть AmneziaWG

Подсеть клиенту выдаётся из `10.20.0.0/16` (10.20.x.0/24 на клиента).

### На bastion:

```bash
ssh ubuntu@mspshield-bastion
cd ~/Newbie
sudo bash technical/0_Common/amneziawg/tenant_add.sh acme 10.20.10.0/24
```

Скрипт напечатает peer-config. Сохранить временно (НЕ в git) для следующего шага.

### На каждом клиентском хосте:

```bash
# На клиентском сервере:
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:amnezia/ppa
sudo apt update && sudo apt install -y amneziawg-dkms amneziawg-tools
sudo mkdir -p /etc/amnezia/amneziawg && sudo chmod 700 /etc/amnezia/amneziawg
sudo tee /etc/amnezia/amneziawg/awg0.conf <<EOF
[Interface]
PrivateKey = <client_private_key>
Address = 10.20.10.11/24

# AmneziaWG обфускация — ИДЕНТИЧные значения как на bastion
# (их выведет tenant_add.sh).
Jc   = 4
Jmin = 50
Jmax = 1000
S1   = 86
S2   = 574
H1   = 1779539752
H2   = 1138729192
H3   = 2050378563
H4   = 8345423

[Peer]
PublicKey = <bastion_server_public_key>
PresharedKey = <psk>
Endpoint = <bastion_public_ip>:443
AllowedIPs = 10.9.0.0/24, 10.20.0.0/16
PersistentKeepalive = 25
EOF
sudo chmod 600 /etc/amnezia/amneziawg/awg0.conf
sudo systemctl enable --now awg-quick@awg0
```

Проверка с bastion:

```bash
ping 10.20.10.11
# PONG
```

---

## Шаг 2. Добавить клиента в Ansible-инвентарь

На control-машине:

```bash
cd technical/0_Common/ansible
```

Отредактировать `inventory/prod.yml`, добавить блок:

```yaml
tenants:
  children:
    acme:                                      # имя клиента
      hosts:
        acme-srv01: { ansible_host: 10.20.10.11 }
        acme-srv02: { ansible_host: 10.20.10.12 }
      vars:
        tier: bronze                           # или silver / gold
        tenant_cidr: 10.20.10.0/24
        patch_window_cron: "0 3 * * 0"         # вс. 03:00 МСК
        alert_tg_chat_id: "-1001234567890"     # отдельный чат этому клиенту
```

Закоммитить (без секретов!):

```bash
git checkout -b devin/$(date +%s)-add-tenant-acme
git add technical/0_Common/ansible/inventory/prod.yml
git commit -m "feat(inventory): добавлен тенант acme (Bronze)"
git push -u origin devin/$(date +%s)-add-tenant-acme
# PR → review → merge
```

---

## Шаг 3. Ansible: baseline + tier-specific роли

### Bronze

```bash
export BASTION_PUBLIC_IP=<из terraform output>
ansible-playbook playbooks/site.yml --limit acme --tags tier_bronze
```

Что настроит:

- baseline hardening (SSH, auditd, fail2ban, unattended-upgrades);
- node_exporter → 9100 (Prometheus будет его scrape'ать);
- restic client + cron еженедельного бэкапа;
- базовые логи → rsyslog (без централизованной аггрегации).

Время: 30–60 мин на первый хост.

### Silver (всё что Bronze +)

```bash
ansible-playbook playbooks/site.yml --limit acme --tags tier_silver
```

Дополнительно:

- `ad_health_check` — ежедневная проверка AD (если есть).
- `loki_client` — централизованные логи в Loki на monitoring-VM.
- Ежедневные (не еженедельные) бэкапы.
- Puppet agent для пользовательских политик (опционально).

### Gold (всё что Silver +)

Gold требует **выездного аудита** + ручной настройки. Ansible делает только baseline; дальше — ручная обвязка Wazuh (SIEM), SOC2-compliance правил, кастомного runbook.

---

## Шаг 4. Бэкапы (restic)

### На каждом клиентском хосте:

```bash
ansible-playbook playbooks/backup_install.yml --limit acme-srv01 -e tier=bronze
```

Плейбук поставит restic и systemd-timer. См. [`../../technical/0_Common/ansible/playbooks/backup_install.yml`](../../technical/0_Common/ansible/playbooks/backup_install.yml).

### Первый бэкап вручную (не ждать cron):

```bash
ssh ubuntu@acme-srv01
sudo /usr/local/sbin/restic-backup.sh
# Проверить:
sudo /usr/local/sbin/restic snapshots
```

### Проверить, что snapshot появился в Object Storage:

```bash
yc storage s3 ls s3://mspshield-backups-prod/acme/
```

---

## Шаг 5. Мониторинг: алёрты клиенту в Telegram и/или MAX

На онбординге спросить клиента какой мессенджер использовать: **Telegram, MAX или оба**. MAX бывает предпочтительнее для российских компаний (льготный режим, отечественный провайдер).

### 5.1. Telegram-вариант

Создать в Telegram группу «MSPShield × Acme — Алёрты», добавить:

- бота `mspshield_alerts_bot` (отдельный от заявочного);
- ответственного со стороны клиента;
- тебя.

Получить `CHAT_ID` (см. раздел 7 в [`landing_production.md`](landing_production.md#7-telegram)).

### 5.2. MAX-вариант

Клиент ставит MAX на рабочий телефон, находит наш бот `@msp_oblako_bot`, пишет `/start` — бот выдаёт ему `chat_id`. Передать его нам — это будет `MAX_ALERT_CHAT_ID` для этого клиента. Подробности: [`docs/MAX_SETUP.md`](../MAX_SETUP.md).

### 5.3. Обновить Alertmanager

```bash
ssh ubuntu@mspshield-landing
sudo nano /etc/alertmanager/alertmanager.yml
# Добавить в routes:
#   - match: { tenant: acme }
#     receiver: tenant_acme
# И в receivers (Telegram-вариант или webhook в backend → MAX):
#   - name: tenant_acme
#     telegram_configs:                                    # если клиент выбрал TG
#       - api_url: https://api.telegram.org
#         bot_token_file: /etc/alertmanager/tg_bot_token
#         chat_id: -1001234567890
#     webhook_configs:                                     # если клиент выбрал MAX (либо оба)
#       - url: https://msp-claude.online/api/alerts/alertmanager
#         http_config:
#           authorization:
#             type: Bearer
#             credentials_file: /etc/alertmanager/max_webhook_token
#         send_resolved: true
sudo systemctl reload alertmanager
```

В backend `/etc/mspshield/backend.env` для MAX-клиента добавить `tenants[acme].max_chat_id` или прописать в базе (см. `backend/integrations/max.py` и поле `max_chat_id` в коллекции `tenants`).

### 5.4. В Prometheus пометить таргеты клиента лейблом `tenant=acme`

Ansible это уже делает через `targets/tenants/acme.yml` (генерируется из inventory).

---

## Шаг 6. Welcome-package клиенту

Отправить email по шаблону из [`../onboarding/welcome_package.md`](../onboarding/welcome_package.md). Содержит:

- пример месячного отчёта (шаблон);
- контактные данные (Telegram / MAX поддержка, email);
- SLA матрицу для его тарифа;
- время weekly-sync (еженедельный 15-мин звонок);
- patch-window договорённости.

---

## Шаг 7. Первый weekly-sync через 7 дней

Календарное событие в Google Calendar, длительность 15 мин.

Повестка:

1. Что успели настроить за неделю (1 мин).
2. Есть ли инциденты / жалобы от сотрудников клиента (3 мин).
3. Прогноз на следующую неделю: что мониторим, где патчим (3 мин).
4. Вопросы клиента (5 мин).
5. Договориться о месячном отчёте (дата + формат).

Вести в Kaiten — карточка «Weekly-sync Acme YYYY-MM-DD».

---

## Чек-лист готовности тенанта

- [ ] AmneziaWG peer работает (`ping 10.20.10.11` с bastion).
- [ ] Ansible site.yml прошёл без ошибок (`--limit acme --tags tier_bronze`).
- [ ] `systemctl status` на всех сервисах клиента — active.
- [ ] Первый restic-снапшот создан (`restic snapshots`).
- [ ] Prometheus-таргеты клиента `UP` (http://localhost:9090/targets).
- [ ] Alertmanager: маршрут `tenant=acme → tenant_acme` работает (тестовый алёрт дошёл в выбранный канал — Telegram и/или MAX).
- [ ] Welcome-package отправлен клиенту, клиент подтвердил получение.
- [ ] Первый weekly-sync запланирован в календаре.
- [ ] Карточка клиента в Kaiten создана со всеми контактами.

---

## Удаление тенанта (offboarding)

Если клиент ушёл:

1. `ansible-playbook playbooks/site.yml --limit acme --tags cleanup`.
2. Удалить peer на bastion: `sudo awg set awg0 peer <client_pubkey> remove`.
3. Экспортировать restic-снапшоты на отдельный диск (оставить у себя 30 дней на случай спора).
4. Через 30 дней — `restic forget --keep-last 0 --prune`.
5. Удалить блок из `inventory/prod.yml`, закоммитить.
6. Удалить Telegram- и/или MAX-чат клиента (в MAX — `/stop` боту + очистить `max_chat_id` в `tenants`).
7. Отменить подписку клиента в Kaiten.
