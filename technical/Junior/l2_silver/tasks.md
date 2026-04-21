# L2 Silver — Практические задачи для Junior
# ═══════════════════════════════════════════════════════════════════

---

## ЗАДАЧА 1: Установить Loki и Promtail

**Цель:** Настроить централизованный сбор логов

**Шаги:**
1. На Monitoring VM: запустить Loki (`docker compose --profile silver up -d loki`)
2. На клиенте: `sudo CLIENT_SLUG=test CLIENT_NAME="Тест" bash install_promtail.sh`
3. В Grafana: Explore → `{client="test"} |= "error"`

**Критерии приёмки:**
```bash
curl -s http://localhost:3100/ready                       # ready
curl -s http://10.9.0.10:9080/ready                       # ready (клиент)
# Grafana Explore: видны логи клиента
```

---

## ЗАДАЧА 2: Настроить Puppet desired state

**Цель:** Puppet автоматически возвращает конфиг к эталону

**Шаги:**
1. На Automation VM: установить Puppet Server
2. На клиенте: `sudo bash install_puppet_agent.sh`
3. Подписать сертификат: `puppetserver ca sign --certname ...`
4. Проверить: `puppet agent --test --verbose`

**Проверка drift (отклонения):**
1. На клиенте: `sudo sed -i 's/PermitRootLogin no/PermitRootLogin yes/' /etc/ssh/sshd_config`
2. Подождать 30 мин (или запустить `puppet agent --test`)
3. Проверить: `grep PermitRootLogin /etc/ssh/sshd_config` → должно быть "no" снова

**Критерии приёмки:**
- [ ] `puppet agent --test` завершается без ошибок
- [ ] Puppet автоматически откатил ручное изменение sshd_config
- [ ] `puppetserver ca list --all` показывает сертификат как "Signed"

---

## ЗАДАЧА 3: Ansible deploy_bronze.yml

**Цель:** Установить все Bronze компоненты одной командой

**Шаги:**
1. На Automation VM: создать inventory для клиента
2. `ansible-playbook playbooks/deploy_bronze.yml -i inventory/clients/test/hosts -v`

**Критерии приёмки:**
```bash
# После playbook:
systemctl is-active node_exporter       # active
systemctl is-active restic-backup.timer  # active
curl -s http://localhost:9100/metrics | head -1  # метрики
```

---

## ЗАДАЧА 4: LogQL — поиск в логах

**Цель:** Научиться искать инциденты в Loki

**Запросы для практики:**
```logql
# Все ошибки за последний час:
{client="test"} |= "error"

# Неудачные SSH входы (брутфорс):
{job="auth", client="test"} |= "Failed password"

# Ошибки Nginx 5xx:
{job="nginx", client="test"} | logfmt | status >= 500

# Топ-5 IP по количеству неудачных входов:
topk(5, sum by (ip) (count_over_time({job="auth"} |= "Failed password" [1h])))
```

**Критерии приёмки:**
- [ ] Может написать LogQL запрос для поиска конкретного события
- [ ] Может отличить `{job="auth"}` от `{job="varlog"}`

---

## ЗАДАЧА 5: Troubleshooting — Promtail не отправляет логи

**Сценарий:** В Grafana Explore нет логов от клиента, но Promtail запущен

**Диагностика:**
1. На клиенте: `systemctl status promtail` → running
2. На клиенте: `curl http://localhost:9080/ready` → ready
3. На клиенте: `journalctl -u promtail -n 50` → "connection refused 10.9.0.1:3100"
4. Проверить VPN: `ping 10.9.0.1` → нет ответа!

**Решение:**
1. `systemctl restart wg-quick@wg0-msp`
2. `ping 10.9.0.1` → OK
3. Подождать 30с, проверить логи в Grafana

**Критерии приёмки:**
- [ ] Логи появились в Grafana
- [ ] Понимает что Promtail → Loki зависит от VPN-канала
