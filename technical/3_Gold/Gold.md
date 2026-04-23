# Gold — Мастер-гайд тарифа
# Версия 3.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# ЭТОТ ФАЙЛ — входная точка для тарифа Gold.
# Gold = Silver + SIEM (Wazuh) + Kaspersky + osTicket + приоритетный SLA
#
# Для кого: Исполнитель (1 человек), Junior-инженер
# ═══════════════════════════════════════════════════════════════════

---

## 1. ЧТО ТАКОЕ GOLD

```
Gold = ВСЁ из Silver ПЛЮС:
  ✓ SIEM: Wazuh Agent → Wazuh Manager → Telegram алерты
  ✓ FIM (File Integrity Monitoring) — контроль изменений файлов
  ✓ Kaspersky Endpoint Security (через GPO + KSC)
  ✓ osTicket — тикет-система для инцидентов
  ✓ SLA P1: реакция до 1 часа, 24/7
  ✓ Стратегические сессии (ежеквартально)

Новое оборудование Исполнителя:
  ✓ Wazuh VM (8 vCPU, 16 GB, 100 GB SSD)
  ✓ osTicket (на Wazuh VM или отдельный контейнер)
```

---

## 2. МАТРИЦА: ЧТО ГДЕ РАЗВОРАЧИВАТЬ

### Сторона КЛИЕНТА (добавляется поверх Silver)

| Компонент | Где устанавливать | SOP | Скрипт | Связь с 0_Common |
|---|---|---|---|---|
| Wazuh Agent | Linux | `CLIENT/SOP_client_gold.md` §1 | `CLIENT/wazuh_agent/install_wazuh_agent_linux.sh` | `0_Common/docker/docker-compose.yml` (profile: gold, wazuh) |
| Wazuh Agent | Windows | `CLIENT/SOP_client_gold.md` §1 | `CLIENT/wazuh_agent/install_wazuh_agent_windows.ps1` | — |
| Wazuh FIM config | Linux/Win | `CLIENT/SOP_client_gold.md` §1 | Встроен в install-скрипты | `3_Gold/EXECUTOR/wazuh/wazuh_manager_ossec.conf` |
| KES deploy | Windows (GPO) | `CLIENT/SOP_client_gold.md` §2 | `CLIENT/kaspersky/kes_deploy_gpo.ps1` | `3_Gold/EXECUTOR/ksc/ksc_setup_guide.md` |
| KES monitoring | Windows | `CLIENT/SOP_client_gold.md` §2 | `CLIENT/kaspersky/monitor_kes.ps1` | `1_Bronze/CLIENT/windows_exporter/` (textfile_collector) |

### Сторона ИСПОЛНИТЕЛЯ (добавляется поверх Silver)

| Компонент | Где разворачивать | SOP | Конфиг | Связь с 0_Common |
|---|---|---|---|---|
| Wazuh VM | Yandex Cloud | `EXECUTOR/SOP_executor_gold.md` §3 | — | — |
| Wazuh Docker Compose | Wazuh VM | `EXECUTOR/SOP_executor_gold.md` §3 | В SOP (inline) | — |
| Wazuh Manager ossec.conf | Wazuh VM | `EXECUTOR/SOP_executor_gold.md` §4 | `EXECUTOR/wazuh/wazuh_manager_ossec.conf` | — |
| Wazuh → Telegram | Wazuh VM | `EXECUTOR/SOP_executor_gold.md` §4 | В SOP (custom-telegram.py) | `0_Common/docker/.env.example` (TG token) |
| KSC setup | Wazuh/Automation VM | `EXECUTOR/SOP_executor_gold.md` §5 | `EXECUTOR/ksc/ksc_setup_guide.md` | — |
| osTicket | Wazuh VM | `EXECUTOR/SOP_executor_gold.md` §6 | `EXECUTOR/osticket/docker-compose.yml` | — |
| Gold alert rules | Monitoring VM | — | `EXECUTOR/gold_alerts.yml` | `1_Bronze/EXECUTOR/prometheus/rules/` |
| deploy_gold.yml | Automation VM | — | `2_Silver/EXECUTOR/ansible/playbooks/deploy_gold.yml` | `0_Common/docker/docker-compose.yml` |

---

## 3. ПОРЯДОК РАЗВЁРТЫВАНИЯ (CHECKLIST)

```
□ Шаги 1–18 из Silver (см. Silver.md §3)             → Silver.md §3
□ Шаг 19. Создать Wazuh VM (8 vCPU, 16 GB)          → SOP_executor_gold.md §3
□ Шаг 20. Настроить ОС Wazuh VM (max_map_count)      → SOP_executor_gold.md §3
□ Шаг 21. Запустить Wazuh Docker Compose             → SOP_executor_gold.md §3
□ Шаг 22. Настроить Wazuh Manager (ossec.conf)       → SOP_executor_gold.md §4
□ Шаг 23. Настроить Wazuh → Telegram                 → SOP_executor_gold.md §4
□ Шаг 24. Установить Wazuh Agent на клиентах         → SOP_client_gold.md §1
□ Шаг 25. Установить KES через GPO                   → SOP_client_gold.md §2
□ Шаг 26. Настроить KSC                              → SOP_executor_gold.md §5
□ Шаг 27. Запустить osTicket                         → SOP_executor_gold.md §6
□ Шаг 28. Добавить gold_alerts.yml                   → В /opt/monitoring/prometheus/rules/
□ Шаг 29. Верификация: verify_all.sh gold            → 0_Common/scripts/verify_all.sh
```

---

## 4. СТОИМОСТЬ GOLD (Исполнитель)

```
Monitoring VM (4 vCPU/8 GB/50 GB SSD):   ~3 800 ₽/мес
Automation VM (2 vCPU/4 GB/40 GB SSD):   ~1 900 ₽/мес
Bastion VM:                              ~600 ₽/мес
Wazuh VM (8 vCPU/16 GB/100 GB SSD):      ~8 500 ₽/мес
Object Storage (~300 ГБ):                ~300 ₽/мес
────────────────────────────────────────────────────────────
Итого инфраструктура:                    ~14 800 ₽/мес (15+ клиентов)

При 15+ клиентах: маржа ~79% на Gold 85k
```

---

## 5. SLA GOLD

| Параметр | Значение |
|---|---|
| P1 (критичный) реакция | 1 час, 24/7 |
| P2 (средний) реакция | 2 часа |
| P3 (низкий) реакция | 8 часов |
| Рабочее время | 24/7 для P1 |
| Wazuh FIM check interval | 12 часов |
| Wazuh vulnerability scan | ежедневно |
| KES database update | автоматически, мониторинг >48ч = alert |

---

## 6. ССЫЛКИ НА ДОКУМЕНТЫ

| Документ | Путь |
|---|---|
| Договор Gold | `contracts/contract_gold.html` |
| SOP Клиент Gold | `3_Gold/CLIENT/SOP_client_gold.md` |
| SOP Исполнитель Gold | `3_Gold/EXECUTOR/SOP_executor_gold.md` |
| Silver мастер-гайд | `2_Silver/Silver.md` |
| Wazuh ossec.conf | `3_Gold/EXECUTOR/wazuh/wazuh_manager_ossec.conf` |
| KSC setup guide | `3_Gold/EXECUTOR/ksc/ksc_setup_guide.md` |
| osTicket compose | `3_Gold/EXECUTOR/osticket/docker-compose.yml` |
| Training Gold-уровень | [`../../docs/training/`](../../docs/training/) (week_03/04) |
