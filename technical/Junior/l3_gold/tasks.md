# L3 Gold — Практические задачи для Junior
# ═══════════════════════════════════════════════════════════════════

---

## ЗАДАЧА 1: Развернуть Wazuh SIEM

**Цель:** Полный цикл — VM → Docker → Agent → FIM → Telegram

**Шаги:**
1. Создать Wazuh VM в Yandex Cloud (8 vCPU, 16 GB)
2. Настроить ОС: `vm.max_map_count=262144`
3. Запустить Wazuh Docker Compose
4. Дождаться инициализации (3–5 мин)
5. Установить Wazuh Agent на клиенте
6. Настроить Telegram интеграцию

**Критерии приёмки:**
```bash
# Wazuh VM:
docker compose ps                           # Все Running
# В Dashboard: логин admin, пароль из /opt/wazuh/.env (WAZUH_INDEXER_PASSWORD)

# Клиент:
systemctl is-active wazuh-agent             # active

# Dashboard (через VPN):
# https://10.9.0.3:443 — виден агент со статусом "Active"
```

---

## ЗАДАЧА 2: FIM — обнаружить изменение файла

**Цель:** Wazuh генерирует алерт при модификации критичного файла

**Шаги:**
1. На клиенте: `echo "test change" >> /etc/hosts`
2. Подождать до 12 часов (FIM interval = 43200с) или уменьшить для теста:
   `sed -i 's/<frequency>43200/<frequency>60/' /var/ossec/etc/shared/agent.conf`
   `systemctl restart wazuh-agent`
3. Проверить в Wazuh Dashboard: Security Events → "syscheck"
4. Проверить Telegram: должен быть алерт level 7+

**Критерии приёмки:**
- [ ] Wazuh Dashboard показывает событие "syscheck" для /etc/hosts
- [ ] Telegram получил уведомление
- [ ] Может объяснить что такое FIM и зачем он нужен

---

## ЗАДАЧА 3: KES мониторинг

**Цель:** Настроить мониторинг статуса антивируса через Prometheus

**Шаги:**
1. На Windows-клиенте: скопировать `monitor_kes.ps1` в `C:\msp-scripts\`
2. Создать Task Scheduler задачу (каждые 5 мин)
3. Проверить: `type "C:\Program Files\windows_exporter\textfile_collector\kaspersky.prom"`

**Критерии приёмки:**
- [ ] `kaspersky.prom` содержит метрики
- [ ] Prometheus видит `kaspersky_service_running` метрику
- [ ] В Grafana видно значение kaspersky_service_running (0 или 1)

---

## ЗАДАЧА 4: SLA alert — алерт не закрыт 45 минут

**Цель:** Понять как работает SLA-мониторинг в Gold

**Сценарий:**
1. Искусственно создать алерт (остановить сервис)
2. НЕ чинить 45+ минут
3. Проверить что `SLAReactionTimeAtRisk` срабатывает
4. Починить, проверить resolved

**Критерии приёмки:**
- [ ] Понимает что Gold SLA P1 = 1 час 24/7
- [ ] Знает что если алерт >45 мин — это риск нарушения SLA
- [ ] Может объяснить зачем osTicket для отслеживания инцидентов

---

## ЗАДАЧА 5: Полная верификация Gold

**Цель:** Запустить verify_all.sh и убедиться что ВСЁ работает

**Шаги:**
```bash
bash /usr/local/bin/verify_all.sh gold
```

**Ожидаемый результат:**
```
══ BRONZE: Docker Compose стек ══
  ✓ Docker запущен
  ✓ Контейнер prometheus
  ✓ Контейнер alertmanager
  ✓ Контейнер grafana
  ...

══ SILVER: Loki ══
  ✓ Контейнер loki
  ✓ Loki /ready
  ...

══ SILVER: Puppet Server ══
  ✓ Puppet Server процесс
  ...

══ GOLD: Wazuh ══
  ✓ Wazuh Manager контейнер
  ✓ Wazuh Indexer контейнер
  ✓ Wazuh Dashboard контейнер
  ...

══ GOLD: osTicket ══
  ✓ osTicket контейнер
  ...

  Пройдено: XX  |  Провалено: 0
  ✅ Все проверки пройдены.
```

**Критерии приёмки:**
- [ ] `verify_all.sh gold` — 0 FAILED
- [ ] Может объяснить каждую секцию верификации
