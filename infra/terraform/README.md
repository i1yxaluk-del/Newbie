# Terraform — Yandex Cloud baseline

## Что в стеке

- VPC + subnet в `ru-central1-a`.
- 2 VM: `mspshield-landing` (2/4) и `mspshield-bastion` (2/2).
- Security-groups с minimal-open портами.
- S3-бакет для restic-бэкапов + service account с ключами.

## Что НЕ в стеке (вынесено отдельно)

- Per-client tenant VMs — отдельный `infra/terraform/tenants/` (generated from Kaiten).
- Vaultwarden VM — `deploy/vaultwarden/` (docker-compose + manual provisioning).
- SIEM/Wazuh для Gold — `infra/terraform/wazuh/` (опциональный, деплоится по tier).

## Подготовка

1. Установить Yandex Cloud CLI:
   ```
   curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
   yc init
   ```
2. Создать S3-бакет для tfstate вручную (через панель YC).
3. Сгенерировать SSH-ключ, положить публичную часть в переменную:
   ```
   ssh-keygen -t ed25519 -f ~/.ssh/mspshield_ed25519
   export TF_VAR_ssh_public_key="$(cat ~/.ssh/mspshield_ed25519.pub)"
   ```
4. Заполнить `terraform.tfvars`:
   ```hcl
   folder_id          = "b1gxxxxxxxxxxxxxxxxx"
   ubuntu_image_id    = "fd8l2fl28s15m3e9u8bi"  # lookup: `yc compute image list ...`
   admin_ssh_sources  = ["203.0.113.5/32"]
   ```

## Развёртывание

```
terraform init
terraform plan
terraform apply
```

Outputs:
- `landing_public_ip`
- `bastion_public_ip`
- `backup_bucket`

## После apply (Ansible)

1. `ansible-playbook -i inventory/prod.yml playbooks/site.yml`.
2. `certbot --nginx -d mspshield.ru -d www.mspshield.ru`.
3. Smoke-test: `curl https://mspshield.ru/api/health`.

## Destroy (аккуратно)

```
terraform destroy
```

⚠ Удалит VM, но **бакет backups** не удалится (force-destroy не включён в ресурсе).
