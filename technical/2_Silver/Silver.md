# Silver — Мастер-гайд тарифа
# Версия 3.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# ЭТОТ ФАЙЛ — входная точка для тарифа Silver.
# Silver = Bronze + логирование + desired state + автоматизация + AD/GPO
#
# Для кого: Исполнитель (1 человек), Junior-инженер
# ═══════════════════════════════════════════════════════════════════

---

## 1. ЧТО ТАКОЕ SILVER

```
Silver = ВСЁ из Bronze ПЛЮС:
  ✓ Централизованные логи (Promtail → Loki → Grafana Explore)
  ✓ Desired State (Puppet Agent → Puppet Server)
  ✓ Автоматизация (Ansible Control Node)
  ✓ Управление AD/DNS/GPO
  ✓ Расширенные отчёты и LogQL-запросы

Новое оборудование Исполнителя:
  ✓ Automation VM (2 vCPU, 4 GB) — Puppet Server + Ansible + Git
  ✓ Monitoring VM апгрейд → 4 vCPU, 8 GB (для Loki)
```

---

## 2. МАТРИЦА: ЧТО ГДЕ РАЗВОРАЧИВАТЬ

### Сторона КЛИЕНТА (добавляется поверх Bronze)

| Компонент | Где устанавливать | SOP | Скрипт | Связь с 0_Common |
|---|---|---|---|---|
| Promtail | Linux | `CLIENT/SOP_client_silver.md` §2 | `CLIENT/promtail/install_promtail.sh` | `0_Common/grafana/loki-config.yml` (куда шлются логи) |
| Promtail config | Linux | `CLIENT/SOP_client_silver.md` §2 | `CLIENT/promtail/promtail-config.yml` | `0_Common/grafana/loki-config.yml` |
| Puppet Agent | Linux | `CLIENT/SOP_client_silver.md` §3 | `CLIENT/puppet_agent/install_puppet_agent.sh` | `0_Common/Puppet_Manifests/` (что применяет Puppet) |
| Puppet Agent | Windows | `CLIENT/SOP_client_silver.md` §3.3 | `CLIENT/puppet_agent/install_puppet_agent_windows.ps1` | `0_Common/Puppet_Manifests/` |
| GPO политики | Windows DC | `CLIENT/SOP_client_silver.md` §4 | `CLIENT/ad_management/gpo_baseline.ps1` | — |

### Сторона ИСПОЛНИТЕЛЯ (добавляется поверх Bronze)

| Компонент | Где разворачивать | SOP | Конфиг | Связь с 0_Common |
|---|---|---|---|---|
| Automation VM | Yandex Cloud | `EXECUTOR/SOP_executor_silver.md` §2 | — | — |
| Loki | Monitoring VM | `EXECUTOR/SOP_executor_silver.md` §3 | `0_Common/grafana/loki-config.yml` | `0_Common/docker/docker-compose.yml` (profile: silver) |
| Loki datasource | Monitoring VM | `EXECUTOR/SOP_executor_silver.md` §3.1 | `1_Bronze/EXECUTOR/grafana/provisioning/datasources/loki.yml` | — |
| Puppet Server | Automation VM | `EXECUTOR/SOP_executor_silver.md` §4 | `EXECUTOR/puppet/` (site.pp + модули) | `0_Common/Puppet_Manifests/` (копии модулей) |
| Ansible Control | Automation VM | `EXECUTOR/SOP_executor_silver.md` §5 | `EXECUTOR/ansible/ansible.cfg` | — |
| deploy_bronze.yml | Automation VM | `EXECUTOR/SOP_executor_silver.md` §5.2 | `EXECUTOR/ansible/playbooks/deploy_bronze.yml` | — |
| deploy_silver.yml | Automation VM | `EXECUTOR/SOP_executor_silver.md` §5.3 | `EXECUTOR/ansible/playbooks/deploy_silver.yml` | — |
| Silver alert rules | Monitoring VM | — | `EXECUTOR/silver_alerts.yml` | `1_Bronze/EXECUTOR/prometheus/rules/` (положить рядом) |

---

## 3. ПОРЯДОК РАЗВЁРТЫВАНИЯ (CHECKLIST)

```
□ Шаги 1–7 из Bronze (см. Bronze.md)                 → Bronze.md §3
□ Шаг 8.  Создать Automation VM                       → SOP_executor_silver.md §2
□ Шаг 9.  Установить Puppet Server                    → SOP_executor_silver.md §4
□ Шаг 10. Установить Ansible Control Node             → SOP_executor_silver.md §5
□ Шаг 11. Добавить Loki в Docker Compose              → SOP_executor_silver.md §3
□ Шаг 12. Проверить Loki: curl localhost:3100/ready   → SOP_executor_silver.md §3
□ Шаг 13. Установить Promtail на клиенте              → SOP_client_silver.md §2
□ Шаг 14. Установить Puppet Agent на клиенте          → SOP_client_silver.md §3
□ Шаг 15. Подписать Puppet сертификат                 → SOP_executor_silver.md §4
□ Шаг 16. Применить GPO (если есть AD)                → SOP_client_silver.md §4
□ Шаг 17. Добавить silver_alerts.yml                  → В /opt/monitoring/prometheus/rules/
□ Шаг 18. Верификация: verify_all.sh silver           → 0_Common/scripts/verify_all.sh
```

---

## 4. СТОИМОСТЬ SILVER (Исполнитель)

```
Monitoring VM (4 vCPU/8 GB/50 GB SSD):   ~3 800 ₽/мес
Automation VM (2 vCPU/4 GB/40 GB SSD):   ~1 900 ₽/мес
Bastion VM (из Bronze):                  ~600 ₽/мес
Object Storage (~200 ГБ):                ~200 ₽/мес
────────────────────────────────────────────────────────────
Итого инфраструктура:                    ~6 500 ₽/мес

Вместимость: 5–15 клиентов
При >15: масштабировать → 0_Common/Scaling/
```

---

## 5. SLA SILVER

| Параметр | Значение |
|---|---|
| P1 (критичный) реакция | 2 часа (рабочее время) |
| P2 (средний) реакция | 4 часа |
| P3 (низкий) реакция | 16 часов |
| Рабочее время | Пн-Пт 09:00–18:00 МСК |
| Puppet run interval | 30 минут |
| Логи retention | 30 дней |

---

## 6. ССЫЛКИ НА ДОКУМЕНТЫ

| Документ | Путь |
|---|---|
| Договор Silver | `contracts/contract_silver.html` |
| SOP Клиент | `2_Silver/CLIENT/SOP_client_silver.md` |
| SOP Исполнитель | `2_Silver/EXECUTOR/SOP_executor_silver.md` |
| Bronze мастер-гайд | `1_Bronze/Bronze.md` |
| Puppet manifests | `0_Common/Puppet_Manifests/` |
| Общий Docker Compose | `0_Common/docker/docker-compose.yml` |
| Junior L2 Silver | `Junior/l2_silver/` |
