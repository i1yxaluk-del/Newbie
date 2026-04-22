# Week 5 · Networking + WireGuard

## Цель

Понимать архитектуру MSPShield overlay: bastion + tenant subnets.
Уметь заводить нового tenant, диагностировать VPN-проблемы.

## Задачи

- [ ] Прочитать `technical/0_Common/wireguard/tenant_add.sh` построчно.
- [ ] Сессия с owner: 1 час про TCP/IP, `iptables` NAT, `ip route`,
      `mtu`.
- [ ] Завести test-tenant на тестовом bastion: сгенерить ключи,
      подключиться с ноутбука, пройти pinog 10.10.0.1.
- [ ] Прочитать R-08 (VPN tunnel down) и разобрать пошагово.

## Production

- [ ] Под supervision завести нового tenant-peer'а для существующего
      клиента (если будет запрос).
- [ ] Отреагировать на один P3 по VPN (если случится в неделю),
      либо симулировать и пройти R-08.

## Read

- WireGuard whitepaper (первые 5 страниц — достаточно).
- `man wg` + `man wg-quick`.

## Check-in

1. Чем WireGuard отличается от OpenVPN и IPsec (в двух словах)?
2. Что такое `AllowedIPs` и зачем?
3. Как проверить, что peer включён и работает?

## DoD

- Развернул test-tenant на своих ресурсах.
- Понимает overlay 10.10/16 и tenant-subnets.
- Может без помощи запустить R-08.
