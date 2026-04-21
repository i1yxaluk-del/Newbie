# Ansible Vault — Руководство по управлению секретами
# Версия 1.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# ДЛЯ JUNIOR: Это ОБЯЗАТЕЛЬНЫЙ документ. Без vault ваши S3-ключи,
# пароли бэкапов и токены ботов будут храниться в открытом виде.
# Любой утечка = потеря данных клиентов.
#
# Что такое ansible-vault:
#   Инструмент шифрования AES-256 для секретов в Ansible-проекте.
#   Позволяет хранить зашифрованные значения прямо в Git.
#   При запуске playbook — vault запрашивает пароль и расшифровывает.
# ═══════════════════════════════════════════════════════════════════

---

## 1. ЧТО ШИФРОВАТЬ

| Секрет | Где хранится | Обязательно vault? |
|---|---|---|
| S3 access key + secret | `inventory/clients/*/vars.yml` | **ДА** |
| Restic repo password | `inventory/clients/*/vars.yml` | **ДА** |
| Telegram Bot Token | `/opt/monitoring/.env` | Нет (env-файл, не Git) |
| Grafana admin password | `/opt/monitoring/.env` | Нет (env-файл, не Git) |
| Wazuh passwords | `/opt/wazuh/.env` | Нет (env-файл, не Git) |
| SMTP password | `/opt/monitoring/.env` | Нет (env-файл, не Git) |
| DB passwords (osTicket) | `/opt/osticket/.env` | Нет (env-файл, не Git) |
| WireGuard private keys | `/etc/wireguard/wg0*.conf` | Нет (на сервере, chmod 600) |

**Правило:** всё что в Git = шифровать vault. Всё что в .env на сервере = `chmod 600` + `.gitignore`.

---

## 2. НАСТРОЙКА VAULT ПАРОЛЯ

### 2.1 Создать файл с паролем vault

```bash
# Пароль для vault — ОДИН на весь проект
# Хранить в безопасном месте (менеджер паролей, NOT в Git!)
openssl rand -base64 32 > ~/.vault_password
chmod 600 ~/.vault_password

# Добавить в .gitignore (уже есть):
echo ".vault_password" >> .gitignore
```

### 2.2 Настроить ansible.cfg

```ini
# В /opt/ansible/ansible.cfg добавить:
[defaults]
vault_password_file = ~/.vault_password
```

---

## 3. СПОСОБ 1: ШИФРОВАНИЕ ВCЕГО ФАЙЛА

```bash
# Зашифровать vars.yml целиком:
ansible-vault encrypt inventory/clients/company1/vars.yml

# Результат: файл выглядит как:
# $ANSIBLE_VAULT;1.1;AES256
# 663864396539666364...

# Расшифровать для редактирования:
ansible-vault edit inventory/clients/company1/vars.yml

# Расшифровать навсегда (НЕ делать! только если нужно перенести):
# ansible-vault decrypt inventory/clients/company1/vars.yml
```

**Плюс:** просто — один файл = один пароль
**Минус:** при редактировании несекретных полей (например, has_nginx: false → true) тоже нужен vault-пароль

---

## 4. СПОСОБ 2: ШИФРОВАНИЕ ОТДЕЛЬНЫХ ЗНАЧЕНИЙ (РЕКОМЕНДУЕТСЯ)

```bash
# Шифруем ТОЛЬКО секретные значения, остальное — открыто

# S3 access key:
ansible-vault encrypt_string 'РЕАЛЬНЫЙ_S3_ACCESS_KEY' --name 'restic_s3_access_key'

# Вывод будет примерно таким:
# !vault |
#   $ANSIBLE_VAULT;1.1;AES256
#   363336343532...

# Скопировать ВЫВОД и вставить в vars.yml вместо строки:
#   restic_s3_access_key: "REPLACE..."
# →
#   restic_s3_access_key: !vault |
#           $ANSIBLE_VAULT;1.1;AES256
#           363336343532...

# Повторить для каждого секрета:
ansible-vault encrypt_string 'РЕАЛЬНЫЙ_S3_SECRET_KEY' --name 'restic_s3_secret_key'
ansible-vault encrypt_string 'РЕАЛЬНЫЙ_REPO_PASSWORD' --name 'restic_repo_password'
```

**Плюс:** можно редактировать несекретные поля без vault-пароля
**Минус:** чуть сложнее при первичном заполнении

---

## 5. ПОЛНЫЙ ПРОЦЕСС ОНБОРДИНГА КЛИЕНТА С VAULT

```bash
# Шаг 1: Создать структуру клиента
CLIENT="company1"
mkdir -p /opt/ansible/inventory/clients/$CLIENT
cp /opt/ansible/roles/inventory_template/vars.yml \
   /opt/ansible/inventory/clients/$CLIENT/vars.yml
cp /opt/ansible/roles/inventory_template/hosts \
   /opt/ansible/inventory/clients/$CLIENT/hosts

# Шаг 2: Заполнить НЕсекретные поля
nano /opt/ansible/inventory/clients/$CLIENT/vars.yml
# client_slug, client_name, client_tier, порты, пути бэкапа...

# Шаг 3: Получить S3-ключи от Yandex Cloud
yc iam access-key create --service-account-name msp-backup-sa \
  --description "client-$CLIENT" | tee /tmp/$CLIENT-s3-keys.json

S3_KEY=$(cat /tmp/$CLIENT-s3-keys.json | jq -r '.access_key.key_id')
S3_SECRET=$(cat /tmp/$CLIENT-s3-keys.json | jq -r '.secret')
RESTIC_PASS=$(openssl rand -hex 32)

# Шаг 4: Зашифровать секреты в vars.yml
cd /opt/ansible

# Способ А: зашифровать весь файл (проще)
ansible-vault encrypt inventory/clients/$CLIENT/vars.yml
# Теперь для редактирования: ansible-vault edit inventory/clients/$CLIENT/vars.yml

# Способ Б: зашифровать только секреты (безопаснее)
ansible-vault encrypt_string "$S3_KEY" --name 'restic_s3_access_key' \
  >> inventory/clients/$CLIENT/vars.yml
ansible-vault encrypt_string "$S3_SECRET" --name 'restic_s3_secret_key' \
  >> inventory/clients/$CLIENT/vars.yml
ansible-vault encrypt_string "$RESTIC_PASS" --name 'restic_repo_password' \
  >> inventory/clients/$CLIENT/vars.yml

# Шаг 5: Удалить временные файлы с ключами
rm /tmp/$CLIENT-s3-keys.json
unset S3_KEY S3_SECRET RESTIC_PASS

# Шаг 6: Проверить что vault работает
ansible-playbook playbooks/deploy_bronze.yml \
  -i inventory/clients/$CLIENT/hosts \
  --ask-vault-pass \
  -v

# Или без --ask-vault-pass если настроен vault_password_file в ansible.cfg

# Шаг 7: Закоммитить в Git (секреты зашифрованы — безопасно!)
git add inventory/clients/$CLIENT/
git commit -m "Add client $CLIENT (vault-encrypted secrets)"
```

---

## 6. .ENV ФАЙЛЫ НА СЕРВЕРАХ (НЕ в Git)

```
.env файлы на серверах НЕ шифруются vault — они не в Git.
Вместо vault для .env:

1. chmod 600 /opt/monitoring/.env       # Только root может читать
2. chmod 600 /opt/wazuh/.env            # Только root может читать
3. chmod 600 /opt/osticket/.env          # Только root может читать
4. chmod 600 /etc/restic/env.sh          # S3 ключи для restic
5. chmod 600 /etc/wireguard/wg0*.conf    # Приватные ключи WG

Генерация паролей для .env (НЕ придумывать вручную!):
  openssl rand -base64 32    # для Grafana, SMTP app password
  openssl rand -base64 24    # для Wazuh, osTicket DB
  openssl rand -hex 32       # для restic repo password

Проверить что .env НЕ в Git:
  git status | grep .env     # НЕ должно быть!
  cat .gitignore | grep .env # Должно быть: .env, .env.*
```

---

## 7. ПРОВЕРКА БЕЗОПАСНОСТИ (CHECKLIST)

```
□ vault_password_file настроен в ansible.cfg
□ ~/.vault_password создан, chmod 600
□ Все inventory/clients/*/vars.yml зашифрованы vault
□ .env файлы на серверах: chmod 600
□ .gitignore содержит: .env, .env.*, .vault_password, *-keys.json
□ WireGuard private keys: chmod 600, НЕ в Git
□ В docker-compose.yml НЕТ fallback-паролей (только ${VAR:?error})
□ В .env.example НЕТ реальных паролей (только __PLACEHOLDER__)
□ ansible-vault view vars.yml — показывает расшифрованные секреты
□ grep -r "SecurePass\|changeme\|rootpasschange\|dbpasschange" . — 0 результатов
```

---

## 8. ЧАСТЫЕ ОШИБКИ

| Ошибка | Почему плохо | Как правильно |
|---|---|---|
| Пароль `admin123` в .env | Легко угадать, бот-сканеры | `openssl rand -base64 32` |
| `${VAR:-default_password}` в compose | Если .env пустой — пароль = default | `${VAR:?VAR must be set in .env}` |
| Fallback `SecurePass123!` | Известный пароль в документации | Убрать fallback, ошибка при отсутствии |
| vars.yml без vault в Git | S3 ключи видны в истории коммитов | `ansible-vault encrypt` перед git add |
| `git add .env` по ошибке | Все секреты в Git навсегда | `.gitignore` + `git rm --cached .env` |
| Восстановление секрета из истории | Даже после удаления — в git history | `git filter-branch` или пересоздать секрет |

---

## 9. РОТАЦИЯ СЕКРЕТОВ

```bash
# Если секрет скомпрометирован (утёк, кто-то увольняется):

# 1. S3 ключи — пересоздать:
yc iam access-key create --service-account-name msp-backup-sa
# Удалить старый ключ в Yandex Cloud Console

# 2. Restic repo password — НЕЛЬЗЯ сменить без пересоздания репо!
# Поэтому: создать новый bucket, инициализировать новый репо,
# скопировать данные через restic copy

# 3. Grafana/Wazuh пароли — сменить в .env + перезапустить контейнер:
nano /opt/monitoring/.env
docker compose restart grafana

# 4. Telegram Bot Token — пересоздать через @BotFather

# 5. Vault password — сменить:
ansible-vault rekey inventory/clients/*/vars.yml
```
