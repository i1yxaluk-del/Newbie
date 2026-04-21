# L1 Bronze — Практические задачи для Junior
# ═══════════════════════════════════════════════════════════════════

---

## ЗАДАЧА 1: Создать WireGuard туннель

**Цель:** Настроить VPN между Monitoring VM и клиентом

**Шаги:**
1. На Monitoring VM: `sudo bash /usr/local/bin/setup_wireguard_bastion.sh`
2. На клиентской VM: `sudo bash /etc/wireguard/setup_wireguard_client.sh`
3. Ввести публичный ключ клиента в Bastion

**Критерии приёмки:**
```bash
# На клиенте:
ping -c 3 10.9.0.1          # OK
sudo wg show wg0-msp        # Виден handshake

# На Bastion:
sudo wg show wg0             # Виден peer клиента
```

---

## ЗАДАЧА 2: Установить мониторинг-стек

**Цель:** Запустить Prometheus + Grafana + Alertmanager

**Шаги:**
1. Скопировать `0_Common/docker/docker-compose.yml` в `/opt/monitoring/`
2. Скопировать `0_Common/docker/.env.example` → `.env`, заполнить
3. `docker compose --profile monitoring up -d`

**Критерии приёмки:**
```bash
curl -s http://localhost:9090/-/healthy     # OK
curl -s http://localhost:9093/-/healthy     # OK
curl -s http://10.9.0.1:3000/api/health    # OK
```

---

## ЗАДАЧА 3: Подключить первый сервер клиента

**Цель:** Установить node_exporter, добавить в Prometheus, увидеть метрики

**Шаги:**
1. На клиенте: `sudo bash install_linux.sh`
2. На Monitoring VM: добавить scrape config в prometheus.yml
3. `curl -X POST http://localhost:9090/-/reload`

**Критерии приёмки:**
```bash
# На Monitoring VM:
curl -s http://10.9.0.10:9100/metrics | head -3  # Видны метрики

# Prometheus targets:
curl -s http://localhost:9090/api/v1/targets | python3 -c "
import sys,json
d=json.load(sys.stdin)
for t in d['data']['activeTargets']:
    if 'client' in str(t.get('labels',{})):
        print(t['labels']['job'], t['health'])
"   # Все UP
```

---

## ЗАДАЧА 4: Настроить бэкап и проверить восстановление

**Цель:** Создать бэкап, проверить что он работает, восстановить файл

**Шаги:**
1. На клиенте: `sudo bash install_restic_linux.sh`
2. Создать тестовый файл: `echo "test" > /tmp/test-restore.txt`
3. Запустить бэкап: `sudo systemctl start restic-backup.service`
4. Восстановить: `restic restore latest --target /tmp/restore --include /tmp/test-restore.txt`
5. Проверить: `cat /tmp/restore/tmp/test-restore.txt`

**Критерии приёмки:**
```bash
restic snapshots              # Виден снапшот
cat /tmp/restore/tmp/test-restore.txt  # = "test"
systemctl is-active restic-backup.timer  # active
```

---

## ЗАДАЧА 5: Сработал алерт — что делать?

**Цель:** Научиться реагировать на алерты

**Сценарий:** Пришёл Telegram алерт: "🔴 CRITICAL | node_exporter down на клиенте"

**Действия:**
1. Проверить: `curl -s http://10.9.0.10:9100/metrics` — нет ответа
2. Подключиться к клиенту: `ssh ubuntu@10.9.0.10`
3. Проверить сервис: `systemctl status node_exporter`
4. Перезапустить: `systemctl restart node_exporter`
5. Проверить: `curl -s http://localhost:9100/metrics | head -3`
6. Проверить в Prometheus что target снова UP

**Критерии приёмки:**
- [ ] Алерт resolved в Alertmanager
- [ ] Target UP в Prometheus
- [ ] Отчёт о инциденте написан (когда, что, как починили)
