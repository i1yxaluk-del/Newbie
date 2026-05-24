# role: `awg_hub`

> AmneziaWG-концентратор на bastion-VM (или совмещённой landing+bastion VM
> с одним публичным IP). Все тенанты подключаются через одну точку,
> Ansible/мониторинг ходят в клиентские сети через `ProxyJump`.
> Сеть 10.10.0.0/16 (mgmt), 10.20.0.0/16 (tenants).
>
> **Почему AmneziaWG, а не WireGuard:** РКН-DPI ловит обычный WG handshake;
> AmneziaWG = форк WG с обфускацией handshake (junk-пакеты, рандомизированная
> длина). Совместим с WG семантически — тот же netlink, kernel-module,
> `prometheus-wireguard-exporter` работает без изменений. См. `docs/runbooks/R-08.md`.

## Что делает

1. Добавляет PPA `ppa:amnezia/ppa` (Ubuntu)
2. `apt install amneziawg-dkms amneziawg-tools qrencode`
3. Включает IP-forward (`/etc/sysctl.d/99-awg.conf`)
4. Создаёт `/etc/amnezia/amneziawg/` (mode 0700)
5. Кладёт `/etc/amnezia/amneziawg/awg0.conf` из template — с параметрами обфускации (Jc/Jmin/Jmax/S1/S2/H1..H4)
6. Открывает UDP `awg_hub_listen_port` в ufw (по умолчанию **UDP/443** — не конфликтует с Caddy TCP/443)
7. `systemctl enable awg-quick@awg0` + start
8. Первичная генерация ключа hub'а — через `awg_bootstrap.sh` (см. `technical/0_Common/amneziawg/awg_bootstrap.sh`); роль ожидает что приватный ключ уже в vault'е

## Переменные

- `awg_hub_interface` (default `awg0`)
- `awg_hub_listen_port` (default `443`)
- `awg_hub_address` (default `10.10.0.1/24`)
- `awg_hub_peers` (list of dicts: `name`, `public_key`, `allowed_ips`)
- `awg_hub_private_key` (**required, vault**)
- **AmneziaWG обфускация** (общая для всех peer'ов): `awg_hub_jc`, `awg_hub_jmin`, `awg_hub_jmax`, `awg_hub_s1`, `awg_hub_s2`, `awg_hub_h1..h4`. Менять только если текущие значения начнут детектиться DPI — изменение требует обновить конфиги у ВСЕХ клиентов.

## Добавление нового тенанта

Не через эту роль напрямую. Используй `tenant_add.sh` на bastion (см.
`technical/0_Common/amneziawg/tenant_add.sh`) — он сгенерит peer-пару,
пропишет peer в `awg0.conf`, и применит `awg syncconf awg0` без drop'а
существующих соединений. Роль при следующем `site.yml` только убедится
что конфиг применён.

См. [`docs/deployment/tenant_onboarding.md`](../../../../docs/deployment/tenant_onboarding.md).
