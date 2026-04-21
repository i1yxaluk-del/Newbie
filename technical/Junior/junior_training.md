# Junior Training Guide — Программа обучения MSPShield
# Версия 3.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# Эта программа обучает Junior-инженера работе с MSP-сервисом.
# 3 уровня: L1 (Bronze), L2 (Silver), L3 (Gold)
# Каждый уровень = теория + практика + критерии приёмки
#
# Порядок обучения: строго L1 → L2 → L3
# Срок: ~4–6 недель (вечер + выходные, 1 человек)
# ═══════════════════════════════════════════════════════════════════

---

## ОБЩИЙ ПЛАН

| Уровень | Тариф | Срок | Что осваивает |
|---|---|---|---|
| L1 | Bronze | 1–2 недели | Мониторинг, бэкапы, VPN, алерты |
| L2 | Silver | 1–2 недели | Логи, Puppet, Ansible, AD/GPO |
| L3 | Gold | 1–2 недели | SIEM, Kaspersky, тикеты, SLA 24/7 |

---

## ФОРМАТ ЗАНЯТИЙ

```
Каждый урок:
  1. ТЕОРИЯ: прочитать SOP (30–60 мин)
  2. ПРАКТИКА: выполнить задание на тестовом стенде (1–3 часа)
  3. ПРОВЕРКА: запустить verify_all.sh + чеклист (15 мин)
  4. Definition of Done (DoD): все пункты выполнены → переход к след. уроку
```

---

## ТЕСТОВЫЙ СТЕНД

```
Для практики нужен стенд. Варианты:
  A) Yandex Cloud trial (60 дней бесплатный) — создать тестовые VM
  B) Локальные VM (VirtualBox/Vagrant) — бесплатно, но без реального Yandex Cloud
  C) Использовать реальную инфраструктуру (если уже есть клиенты)

МИНИМУМ для тестового стенда:
  - 1 Linux VM (Ubuntu 22.04) — "Monitoring VM + Bastion"
  - 1 Linux VM — "клиентский сервер"
  - 1 Windows VM (опционально) — "клиентский Windows"
```

---

## L1: BRONZE — ОСНОВЫ

### Урок L1.1: WireGuard VPN

**Теория:**
- Прочитать: `1_Bronze/CLIENT/SOP_client_bronze.md` §3
- Прочитать: `1_Bronze/EXECUTOR/SOP_executor_bronze.md` §4
- Понять: зачем VPN, как работают ключи, IP-схема 10.9.0.0/24

**Практика:**
1. Создать Monitoring VM в Yandex Cloud
2. Установить WireGuard Bastion (серверную часть)
3. Создать тестовый клиент Linux VM
4. Настроить WireGuard client
5. Проверить: `ping 10.9.0.1` с клиента

**DoD:**
- [ ] `wg show wg0` показывает handshake на обоих концах
- [ ] `ping 10.9.0.1` с клиентской VM успешен
- [ ] Конфиг `/etc/wireguard/wg0-msp.conf` имеет `chmod 600`

### Урок L1.2: Docker Compose Monitoring Stack

**Теория:**
- Прочитать: `1_Bronze/EXECUTOR/SOP_executor_bronze.md` §5
- Понять: Docker Compose profiles, Prometheus scrape, Grafana provisioning

**Практика:**
1. Создать `/opt/monitoring/` структуру
2. Скопировать `0_Common/docker/docker-compose.yml` и `.env.example`
3. Заполнить `.env` (генерировать пароли, создать Telegram бота)
4. Запустить: `docker compose --profile monitoring up -d`
5. Открыть Grafana через VPN: http://10.9.0.1:3000

**DoD:**
- [ ] Все контейнеры Running: `docker compose ps`
- [ ] Prometheus healthy: `curl localhost:9090/-/healthy`
- [ ] Grafana доступна через VPN
- [ ] `verify_all.sh bronze` — 0 FAILED

### Урок L1.3: Node Exporter + Windows Exporter

**Теория:**
- Прочитать: `1_Bronze/CLIENT/SOP_client_bronze.md` §4,5
- Понять: что такое exporters, метрики, textfile_collector

**Практика:**
1. Установить `node_exporter` на Linux-клиенте через скрипт
2. Установить `windows_exporter` на Windows-клиенте (если есть)
3. Добавить клиента в Prometheus (настроить prometheus.yml)
4. Проверить: `curl http://10.9.0.10:9100/metrics` с Bastion

**DoD:**
- [ ] `node_exporter` отдаёт метрики на клиенте
- [ ] Prometheus target "UP" для клиента
- [ ] Grafana показывает метрики клиента

### Урок L1.4: Restic Backup

**Теория:**
- Прочитать: `1_Bronze/CLIENT/SOP_client_bronze.md` §6
- Понять: S3-бэкапы, retention policy, метрики бэкапа

**Практика:**
1. Создать S3-bucket в Yandex Object Storage
2. Установить restic + настроить backup.sh
3. Запустить первый бэкап вручную
4. Проверить: `restic snapshots`

**DoD:**
- [ ] Бэкап успешно создан (restic snapshots показывает снапшот)
- [ ] Timer активен: `systemctl list-timers restic-backup.timer`
- [ ] Метрика `restic_backup_last_status` = 1

### Урок L1.5: Alert Rules + Alertmanager

**Теория:**
- Прочитать: `1_Bronze/EXECUTOR/prometheus/rules/bronze_alerts.yml`
- Прочитать: `1_Bronze/EXECUTOR/alertmanager/alertmanager.yml`
- Понять: severity levels, for-clause, routing, inhibition

**Практика:**
1. Убрать `for: 5m` с тестового алерта (чтобы сработал быстро)
2. Остановить node_exporter на клиенте: `systemctl stop node_exporter`
3. Дождаться алерта в Prometheus: `curl localhost:9090/api/v1/alerts`
4. Проверить что Telegram получил сообщение
5. Запустить node_exporter обратно

**DoD:**
- [ ] Алерт сгенерирован при остановке сервиса
- [ ] Telegram бот получил уведомление
- [ ] Алерт автоматически resolved после восстановления

---

## L2: SILVER — АВТОМАТИЗАЦИЯ

### Урок L2.1: Loki + Promtail

**Теория:**
- Прочитать: `2_Silver/EXECUTOR/SOP_executor_silver.md` §3
- Прочитать: `2_Silver/CLIENT/SOP_client_silver.md` §2
- Понять: LogQL, labels, pipeline stages, positions.yaml

**Практика:**
1. Добавить Loki в Docker Compose (profile: silver)
2. Установить Promtail на клиенте через `install_promtail.sh`
3. Выполнить LogQL запросы в Grafana Explore
4. Попробовать: `{client="test"} |= "error"`

**DoD:**
- [ ] Loki /ready отвечает
- [ ] Promtail запущен на клиенте
- [ ] Логи видны в Grafana Explore

### Урок L2.2: Puppet Server + Agent

**Теория:**
- Прочитать: `2_Silver/EXECUTOR/SOP_executor_silver.md` §4
- Прочитать: `2_Silver/CLIENT/SOP_client_silver.md` §3
- Понять: desired state, certificates, modules, site.pp

**Практика:**
1. Создать Automation VM
2. Установить Puppet Server
3. Установить Puppet Agent на клиенте
4. Подписать сертификат
5. Проверить что `base_linux` класс применён

**DoD:**
- [ ] Puppet Agent успешно выполняет `puppet agent --test`
- [ ] Изменение /etc/motd через Puppet видно на клиенте
- [ ] Puppet обнаруживает drift (изменить файл вручную, проверить)

### Урок L2.3: Ansible Playbooks

**Теория:**
- Прочитать: `2_Silver/EXECUTOR/SOP_executor_silver.md` §5
- Прочитать: `2_Silver/EXECUTOR/ansible/playbooks/deploy_bronze.yml`
- Понять: inventory, roles, tags, vars_files

**Практика:**
1. Настроить Ansible Control Node
2. Создать inventory для тестового клиента
3. Запустить `deploy_bronze.yml`
4. Запустить `deploy_silver.yml`

**DoD:**
- [ ] Ansible успешно устанавливает все Bronze компоненты
- [ ] Ansible успешно устанавливает Silver компоненты (Promtail, Puppet)
- [ ] `verify_all.sh silver` — 0 FAILED

### Урок L2.4: AD/GPO Management

**Теория:**
- Прочитать: `2_Silver/CLIENT/SOP_client_silver.md` §4
- Прочитать: `2_Silver/CLIENT/ad_management/gpo_baseline.ps1`
- Понять: GPO, OU, FGPP, аудит

**Практика:**
1. Запустить `gpo_baseline.ps1` на тестовом DC (если есть)
2. Или изучить скрипт и объяснить каждую секцию

**DoD:**
- [ ] Может объяснить зачем нужна парольная политика с complexity
- [ ] Может объяснить что делает GPO MSP-Security-Baseline
- [ ] Знает команду `gpresult /r` для проверки применения GPO

---

## L3: GOLD — БЕЗОПАСНОСТЬ

### Урок L3.1: Wazuh SIEM

**Теория:**
- Прочитать: `3_Gold/CLIENT/SOP_client_gold.md` §1
- Прочитать: `3_Gold/EXECUTOR/SOP_executor_gold.md` §3,4
- Понять: SIEM, FIM, vulnerability detector, agent enrollment

**Практика:**
1. Создать Wazuh VM
2. Запустить Wazuh Docker Compose
3. Установить Wazuh Agent на клиенте
4. Настроить FIM (изменить файл, проверить алерт)
5. Настроить Telegram интеграцию

**DoD:**
- [ ] Wazuh Dashboard доступен через VPN
- [ ] Agent "Active" в Wazuh Manager
- [ ] FIM алерт сгенерирован при изменении /etc/passwd
- [ ] Telegram получил Wazuh алерт

### Урок L3.2: Kaspersky Endpoint Security

**Теория:**
- Прочитать: `3_Gold/CLIENT/SOP_client_gold.md` §2,3
- Прочитать: `3_Gold/EXECUTOR/ksc/ksc_setup_guide.md`
- Понять: KES deployment через GPO, KSC, мониторинг

**Практика:**
1. Установить `monitor_kes.ps1` на Windows-клиенте (даже без KES — скрипт покажет 0)
2. Проверить метрику в Prometheus: `kaspersky_service_running`
3. Изучить `gold_alerts.yml` — KasperskyNotRunning, KasperskyDatabaseOld

**DoD:**
- [ ] `monitor_kes.ps1` пишет kaspersky.prom
- [ ] Метрика видна в Prometheus
- [ ] Может объяснить почему KES ставится через GPO а не вручную

### Урок L3.3: osTicket + SLA Monitoring

**Теория:**
- Прочитать: `3_Gold/EXECUTOR/SOP_executor_gold.md` §6
- Понять: тикет-система, SLA P1=1ч 24/7, SLA alerting

**Практика:**
1. Запустить osTicket Docker Compose
2. Создать тестовый тикет
3. Проверить SLA alert rule: `SLAReactionTimeAtRisk`

**DoD:**
- [ ] osTicket доступен через VPN
- [ ] Может создать тикет
- [ ] Понимает что SLA alert сработает если алерт не закрыт 45 мин
- [ ] `verify_all.sh gold` — 0 FAILED

---

## ФИНАЛЬНАЯ ПРОВЕРКА

### После завершения L3 Junior должен уметь:

**Самостоятельно (без подсказок):**
- [ ] Создать Yandex Cloud VM и настроить WireGuard
- [ ] Запустить мониторинг-стек Docker Compose
- [ ] Установить все агенты на клиентских серверах
- [ ] Настроить alert rules и проверить Telegram
- [ ] Выполнить `verify_all.sh` и интерпретировать результат
- [ ] Устранить типичные проблемы (VPN нет handshake, exporter down, backup fail)

**С подсказками (по документации):**
- [ ] Установить Puppet Server + подписать сертификаты
- [ ] Написать Ansible playbook для нового типа агента
- [ ] Настроить Wazuh FIM для нового приложения
- [ ] Создать GPO для нового требования безопасности

---

## РЕСУРСЫ ДЛЯ ОБУЧЕНИЯ

| Тема | Ресурс |
|---|---|
| WireGuard | https://www.wireguard.com/quickstart/ |
| Prometheus | https://prometheus.io/docs/introduction/overview/ |
| Grafana | https://grafana.com/tutorials/ |
| Loki + LogQL | https://grafana.com/docs/loki/latest/query/ |
| Puppet | https://puppet.com/docs/puppet/8/puppet_overview.html |
| Ansible | https://docs.ansible.com/ansible/latest/getting_started/ |
| Wazuh | https://documentation.wazuh.com/ |
| Yandex Cloud | https://cloud.yandex.ru/docs/ |
