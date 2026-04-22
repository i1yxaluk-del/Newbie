# Day 1–7 onboarding runbook

> После pre-onboarding (см. `pre_onboarding_checklist.md`).
> Длительность: Bronze 3 дн, Silver 5 дн, Gold 7 дн.

---

## Day 1 · Kick-off + первые scans

**Задачи:**
- [ ] Встреча kick-off с клиентом (45 мин).
  - Представить команду.
  - Перечислить все runbook-действия на 7 дней.
  - Подтвердить контакты для P1-P4.
  - Договориться о регулярной weekly встрече.
- [ ] Discovery-scan через Ansible ad-hoc:
  ```
  ansible <client_inventory> -m setup > facts/<client>.json
  ```
- [ ] Собрать baseline-метрики (CPU, RAM, disk, network).
- [ ] Первый полный dump всех конфигов в приватный git-репо MSP:
  ```
  technical/<tier>/<client>/as_is_YYYY-MM-DD/
  ```
- [ ] Ротация паролей админов (новые — только у MSP + клиента в Vaultwarden).

**Результат Day 1:** клиент подключён к мониторингу в read-only режиме.

---

## Day 2 · Бэкапы

- [ ] Проверить текущую backup-стратегию клиента (если есть).
- [ ] Развернуть restic-клиент на всех серверах из Ansible playbook:
  ```
  ansible-playbook playbooks/backup_install.yml -e tier=<bronze|silver|gold>
  ```
- [ ] Настроить расписание (cron/systemd-timer):
  - Bronze: daily full + 24h retention.
  - Silver: daily incremental + weekly full, 30d retention.
  - Gold: 4-hourly incremental + daily full, 90d retention.
- [ ] S3-репозиторий инициализирован.
- [ ] **Первый полный бэкап прошёл.**
- [ ] **Тест-restore** одного файла из бэкапа — задокументирован.

**Результат Day 2:** бэкап работает, RPO подтверждён.

---

## Day 3 · Мониторинг полностью

- [ ] Prometheus exporters на всех серверах (`node_exporter`, для Silver/Gold — `postgres_exporter`, `mysql_exporter`, по необходимости).
- [ ] Все таргеты видны в Prometheus (`file_sd` обновлён).
- [ ] Dashboard Grafana для клиента создан из template:
  - Infra overview
  - Disk usage
  - Service status (systemd units)
  - Backup status
- [ ] Alertmanager: все правила из base-set-rules применены.
- [ ] Тестовый алерт прошёл в Telegram клиента.
- [ ] Клиенту отправлен read-only URL Grafana.

**Результат Day 3:** клиент видит dashboard, алерты доходят.

---

## Day 4 · Security basics

- [ ] SSH: запрещён root login, ключи заменены на новые, fail2ban включён.
- [ ] Firewall: только нужные порты, все остальные закрыты (ufw/nftables).
- [ ] Auto-update security patches: включены для ОС.
- [ ] Sudoers: правила редизайнены, лог пишется в `/var/log/sudo.log`.
- [ ] Rsyslog → Loki: логи собираются.
- [ ] Fail2ban действует (проверка — 3 wrong логина → ban).
- [ ] Time sync: NTP настроен.
- [ ] **Gold:** Wazuh-агенты установлены.
- [ ] **Gold:** Kaspersky KSC агенты установлены.

**Результат Day 4:** baseline security posture.

---

## Day 5 · Конфигурация by-tier

### Bronze
- [ ] Puppet: базовый hardening profile applied.
- [ ] Конфиги NAS/файлсервера задокументированы.
- [ ] Проверены SSL-сертификаты, срок ≥ 60 дней.

### Silver (additional)
- [ ] AD health check (dcdiag + repadmin).
- [ ] GPO inventory.
- [ ] Puppet master настроен, node signed.
- [ ] Ansible inventory финализирован.
- [ ] Первый deployment nginx конфига через CI.

### Gold (additional)
- [ ] Wazuh: все агенты «active», dashboard доступен.
- [ ] SIEM-rules adapted для клиентских сервисов.
- [ ] Compliance-scan (OpenSCAP / CIS benchmark) пройден, отчёт в Kaiten.
- [ ] osTicket instance клиенту dedicated (для Gold).
- [ ] Kaspersky policies применены.

---

## Day 6 · Runbooks и передача знаний

- [ ] Клиенту отправлены все runbook-ссылки (приоритет 1).
- [ ] Team-training 30 мин с ключевыми сотрудниками клиента:
  - Что делать при сбое.
  - Как связаться с MSP.
  - Что НЕ делать (не ребутить критические серверы без запроса, etc).
- [ ] Клиент получил welcome-package (см. `welcome_package.md`).
- [ ] Создан Kaiten-шаблон для тикетов клиента.

**Результат Day 6:** клиент понимает, как жить с нами.

---

## Day 7 · Go-live + первый weekly-sync

- [ ] Финальный check-list onboarding.
- [ ] Режим работы переключается с «onboarding» на «production» в Kaiten.
- [ ] SLA активирован (с этого момента отсчитываются штрафы за нарушения).
- [ ] Первый weekly-sync с клиентом (30 мин):
  - Что сделали за 7 дней.
  - Какие были нюансы.
  - Что в плане на ближайшую неделю.
  - Обратная связь от клиента.
- [ ] Создан первый «ежемесячный отчёт» (placeholder, заполняется в конце месяца).

**Результат Day 7:** клиент в production, monitoring-retention считается, SLA live.

---

## Acceptance criteria

Клиент считается «onboarded» (переход стадия 6 в sales-воронке), если:

1. Все runbook-шаги 1-7 выполнены.
2. Клиент подтвердил, что получил welcome-package.
3. Клиент хотя бы 1 раз воспроизвёл «вызов поддержки» (drill).
4. Успешный test-restore бэкапов задокументирован.
5. Grafana-dashboard доступен клиенту.
6. Weekly-sync прошёл, обратная связь получена.

---

## Риски онбординга

| Риск | Митигация |
|---|---|
| Клиент не даёт доступы вовремя | Pre-onboarding до оплаты + жёсткие дедлайны |
| Инфра оказалась сильно хуже ожидаемого | В договоре пункт «если требуется capital rebuild — отдельный проект по ADDON» |
| Ключевой сотрудник клиента на отпуске в Day 1–5 | Договариваться о delay onboarding на неделю |
| Технический долг требует сначала ADDON (миграция, AD-cleanup) | Предложить его как paid project до основного onboarding |

---

## Отклонения от runbook

Любое отклонение (пропуск шага, откладывание) — записать в Kaiten
с обоснованием. Это будет входить в ежемесячный отчёт клиенту
и quarterly review внутри MSP.

---

*Обновлено: v4.1 · 2026-04*
