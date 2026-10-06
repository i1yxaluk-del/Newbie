# Де-комиссия Jami (06.10.2026)

Jami-пилот завершён: основной мессенджер — **XMPP** (Prosody, `x.msp-claude.online`,
invite-портал `invite.msp-claude.online`). Стек Jami выведен из эксплуатации
на VM `msp-cloud-vm` (cloud.ru).

## Что удалено

- **Сервисы:** `jams.service` (JAMS), `jamiserver.service` (jamid), `dhtnode.service` (OpenDHT).
- **Контейнеры:** `jami-invite`, `jami-nameservice`, `jami-pg`, `jami-exporter`.
- **Пакеты:** `jami-daemon`, `dhtnode` (+ автоочистка зависимостей).
- **Каталоги:** `/opt/jams`, `/opt/jams-src`, `/opt/jami-services`, `/opt/jdk26`, `/opt/maven`.
- **Пользователи:** `jamiserver`, `jams`, `dht`, `opendht`; юнит-файлы и want-ссылки.
- **Caddy:** блоки `dht.*`, `names.*` убраны; `m.*` — заглушка (404), зарезервирован под Matrix.
- **Сеть:** ufw и Security Group cloud.ru — правила `4222/tcp+udp` (OpenDHT) удалены.
- **Мониторинг:** `rules/jami.yml`, job `jami` (`jami-exporter:8892`), blackbox-пробы
  `names.`/`dht.`, дашборд `jami.json`, `jami-host-metrics.sh`.

Архив удалённых конфигов на VM: `/opt/archive/jami-2026-10-06/` (включая скрипт де-комиссии).

## Что осталось и зачем

- **coturn** — TURN для XMPP-звонков; креды клиентам выдаёт Prosody (XEP-0215, mod_turn_external).
- **ntfy** — push (UnifiedPush); переехал в `/opt/ntfy` (compose в репо: `deploy/ntfy/`).
- **Caddy `turn.*`** — блок-держатель сертификата для coturn (веб-морды нет, 404).
- **`m.msp-claude.online`** — заглушка, ждёт Matrix.

## Проверки после де-комиссии

- XMPP c2s `5222` снаружи: TCP + STARTTLS — ОК; invite-портал `/health` — 200; `push.` — 200.
- Почта (Stalwart) не затрагивалась: контейнер healthy, порты 25/143/465/587/993 на месте.
  (PTR-записи для доставляемости сделаны техподдержкой cloud.ru — не трогать.)
- Мониторинг: 14 целей, все up; Jami-проб нет.
- Диск: 83% → 77% занятости (освобождено ~1.7 ГБ).

## Осталось вручную

- **DNS (Namecheap):** удалить A-записи `dht` и `names` (ведут на снятые сервисы).
  Остаются: `@`, `www`, `mail`, `m` (под Matrix), `e` (под Element), `x`, `con`, `invite`, `turn`, `push`, `mon`, `vault`.

## Откат

- Снимок restic снят автоматически перед удалением (06.10.2026 09:33, «Backup завершён успешно»).
- Исходники стека сохранены в git (`deploy/jami-services/`, история коммитов).
