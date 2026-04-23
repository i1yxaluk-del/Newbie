# role: `wireguard_hub`

> WireGuard-концентратор на bastion-VM. Все тенанты подключаются через одну точку,
> Ansible/мониторинг ходят в клиентские сети через `ProxyJump`. Сеть 10.10.0.0/16 (mgmt), 10.20.0.0/16 (tenants).

## Что делает

1. `apt install wireguard wireguard-tools qrencode`
2. Включает IP-forward (`/etc/sysctl.d/99-wg.conf`)
3. Кладёт `/etc/wireguard/wg0.conf` из template
4. Оборачивает первичный bootstrap: если ключа hub нет — вызывает `wg_bootstrap.sh` (см. `technical/0_Common/wireguard/wg_bootstrap.sh`)
5. Открывает UDP `wg_hub_listen_port` в ufw
6. `systemctl enable wg-quick@wg0` + start

## Переменные

- `wg_hub_listen_port` (default `51820`)
- `wg_hub_address` (default `10.10.0.1/24`)
- `wg_hub_peers` (list of dicts: `name`, `public_key`, `allowed_ips`)
- `wg_hub_private_key` (required, vault)

## Добавление нового тенанта

Не через эту роль напрямую. Используй `tenant_add.sh` на bastion — он сгенерит peer-пару, пропишет peer в `wg0.conf`, обновит inventory. Роль при следующем `site.yml` только убедится что конфиг применён.

См. `docs/deployment/tenant_onboarding.md`.
