# Week 5 · Networking + AmneziaWG

## Цель

Понимать архитектуру MSPShield overlay: bastion + tenant subnets.
Уметь заводить нового tenant, диагностировать VPN-проблемы.

## Задачи

- [ ] Прочитать `technical/0_Common/amneziawg/tenant_add.sh` построчно.
- [ ] Сессия с owner: 1 час про TCP/IP, `iptables` NAT, `ip route`,
      `mtu`.
- [ ] Завести test-tenant на тестовом bastion: сгенерить ключи,
      подключиться с ноутбука, пройти pinog 10.9.0.1.
- [ ] Прочитать R-08 (VPN tunnel down) и разобрать пошагово.
- [ ] ⚠️ **Урок из деплоя:** На test-VM проверить SSH-опции для
      preemptible: `-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL`.
      Обсудить с owner почему это важно (host keys меняются при рестарте,
      без static IP DNS устаревает). См. `deploy/yandex/README.md` §10.0.3.

## Production

- [ ] Под supervision завести нового tenant-peer'а для существующего
      клиента (если будет запрос).
- [ ] Отреагировать на один P3 по VPN (если случится в неделю),
      либо симулировать и пройти R-08.

## Read

- AmneziaWG whitepaper (первые 5 страниц — достаточно).
- `man awg` + `man awg-quick`.

## Check-in

1. Чем AmneziaWG отличается от OpenVPN и IPsec (в двух словах)?
2. Что такое `AllowedIPs` и зачем?
3. Как проверить, что peer включён и работает?

## DoD

- Развернул test-tenant на своих ресурсах.
- Понимает overlay 10.9/24 и tenant-subnets.
- Может без помощи запустить R-08.
