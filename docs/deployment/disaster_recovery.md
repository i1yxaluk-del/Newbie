# Disaster Recovery

Что делать, если прод упал. Короткий практический план.

Для клиентских инцидентов — отдельные runbook'и: [`../runbooks/R-01.md`](../runbooks/R-01.md) … [`R-11.md`](../runbooks/R-11.md).
Этот документ — про **нашу** инфраструктуру (landing + bastion + мониторинг).

---

## Сценарий 1: Лендинг недоступен (https://msp-claude.online не открывается)

### Первые 5 минут

```bash
# 1. Проверить DNS:
dig +short msp-claude.online
# Должен быть <landing_public_ip>

# 2. Проверить доступность по IP:
curl -I http://<landing_public_ip>/api/health
# Если 200 — проблема в DNS / certbot / nginx SSL.
# Если нет ответа — проблема в VM / сети.

# 3. Зайти на VM:
ssh ubuntu@mspshield-landing  # через bastion

# 4. Проверить сервисы:
sudo systemctl status nginx mspshield-backend mongodb
```

### Типовые причины

| Симптом | Причина | Фикс |
|---------|---------|------|
| `502 Bad Gateway` | FastAPI упал | `sudo systemctl restart mspshield-backend` → смотреть `journalctl -u mspshield-backend -n 100` |
| `SSL_ERROR` в браузере | Сертификат истёк | `sudo certbot renew --force-renewal -d msp-claude.online` |
| `ERR_CONNECTION_REFUSED` | nginx упал | `sudo systemctl restart nginx` |
| `404` на корне | Пропал build | Передеплоить frontend: `ansible-playbook playbooks/site.yml --limit landing --tags frontend` |
| Timeout по IP | VM упала / Yandex Cloud-проблема | Проверить в консоли Yandex Cloud; если VM running — `ssh` с verbose; если stopped — `yc compute instance start` |
| DNS не резолвится | У регистратора проблема | Проверить `dig @ns1.reg.ru msp-claude.online`; в крайнем случае — временно на публичный IP |

### Эскалация

Если больше 15 минут не решается, и клиенты Gold/Silver активны:

1. Написать в клиентские чаты: «Лендинг недоступен, клиентские сервисы НЕ затронуты (они на отдельных VM)».
2. Сосредоточиться на починке; НЕ параллелить с другими делами.

---

## Сценарий 2: Bastion упал (нет доступа к клиентским хостам)

### Последствия

- **НЕ** затрагивает клиентский сервис (AmneziaWG peer-to-peer работает напрямую, если настроен `PersistentKeepalive`, но на практике AmneziaWG через hub).
- **Затрагивает** наш доступ к клиентам → мы не можем отреагировать на их инциденты.
- **Затрагивает** Prometheus scrape → ложные алёрты «Instance down».

### План восстановления

```bash
# 1. Проверить статус VM:
yc compute instance get mspshield-bastion

# 2. Если STOPPED — запустить:
yc compute instance start mspshield-bastion

# 3. Если RUNNING но нет SSH:
# Попробовать serial console в Yandex Cloud UI.

# 4. Если VM целиком умерла — terraform apply пересоздаст её:
cd infra/terraform
terraform apply -replace=yandex_compute_instance.bastion
# ВАЖНО: публичный IP изменится! Надо:
#   - Обновить ansible.cfg (BASTION_PUBLIC_IP).
#   - Обновить Endpoint у всех клиентов в их /etc/amnezia/amneziawg/awg0.conf.
#   - AmneziaWG сервер-ключи нужно восстановить из бэкапа (см. ниже).
```

### Восстановление AmneziaWG-ключей

Если `/etc/amnezia/amneziawg/` пропал вместе с VM:

1. Достать последний restic-снапшот bastion-ключей (`restic snapshots --host mspshield-bastion`).
2. Восстановить `/etc/amnezia/amneziawg/server_private.key`, `/etc/amnezia/amneziawg/awg0.conf`, `/etc/amnezia/amneziawg/tenants/`.
3. `sudo systemctl restart awg-quick@awg0`.

Если снапшотов нет (не должно быть, но всякое бывает):

- Пересоздать ключи (`awg_bootstrap.sh`).
- **Все клиенты пересоздаются**: `tenant_add.sh` → передать новые конфиги клиентам → они обновляют у себя.

**Время:** 30 мин с снапшотом, 2–4 часа без.

---

## Сценарий 3: Данные заявок пропали (MongoDB упала/побилась)

### Есть ли бэкап

```bash
ssh ubuntu@mspshield-landing
sudo restic snapshots --host mspshield-landing --path /var/lib/mongodb
```

### Восстановление

```bash
# 1. Остановить backend и mongo:
sudo systemctl stop mspshield-backend mongodb

# 2. Восстановить данные:
sudo restic restore <snapshot_id> --target /tmp/mongo-restore --include /var/lib/mongodb

# 3. Заменить:
sudo mv /var/lib/mongodb /var/lib/mongodb.broken
sudo mv /tmp/mongo-restore/var/lib/mongodb /var/lib/mongodb
sudo chown -R mongodb:mongodb /var/lib/mongodb

# 4. Запустить:
sudo systemctl start mongodb mspshield-backend

# 5. Проверить:
curl -H "X-Admin-Token: ..." https://msp-claude.online/api/leads | jq length
```

---

## Сценарий 4: Полная потеря инфры (метеорит в Yandex Cloud)

Очень маловероятно, но план нужен.

### Что у нас есть

- Terraform state в S3-бакете `mspshield-tfstate` (другой регион? — нет, один; **слабое звено**).
- Код в GitHub.
- Restic-бэкапы данных в S3-бакете `mspshield-backups-new`.
- Vaultwarden бэкап в отдельном S3-бакете.

### План

1. **Если tfstate-бакет жив**: `terraform apply` → AmneziaWG bootstrap → Ansible site.yml → восстановить MongoDB из restic → обновить DNS. **Время:** 4–6 часов.
2. **Если tfstate-бакет умер тоже**: `terraform init` с нуля → `terraform import` существующих ресурсов (если остались), иначе — `apply` с нуля → всё заново. **Время:** 1–2 дня.
3. **Если всё в Yandex Cloud умерло**: перенос в VK Cloud / Selectel. **Время:** 3–7 дней. Единственные данные, которые не потеряются — код в GitHub и бэкапы в S3 (при условии, что восстановим S3-ключи из Vaultwarden-бэкапа).

### Улучшения (TODO)

- [ ] Бэкап tfstate в отдельный регион / провайдера (v4.2).
- [ ] Бэкап Vaultwarden в Box.com / Google Drive помимо Yandex S3 (v4.2).
- [ ] Документ «Runbook BCP» с контактами облачных провайдеров.

---

## Практика: квартальный DR-drill

Раз в квартал (см. [`../checklists/quarterly.md`](../checklists/quarterly.md)):

1. Для одного тенанта — `./technical/0_Common/scripts/dr_drill.sh acme` (smoke).
2. Раз в 6 мес — `dr_drill.sh acme --full`.
3. Результаты — в retrospective doc спринта.

Если drill провалился — **P0**, роадмап откладывается до фикса.

---

## Связанные документы

- [`../runbooks/`](../runbooks/) — реагирование на клиентские инциденты.
- [`../post_mortem_template.md`](../post_mortem_template.md) — шаблон post-mortem после серьёзных инцидентов.
- [`troubleshooting.md`](troubleshooting.md) — мелкие траблы.
