# Уроки deployment и migration — применённые решения

Документ отделяет наблюдение от внедрённого контроля. Формулировка «урок учтён» допустима только при наличии кода, проверки и runbook.

## Матрица

| Урок | Риск | Внедрённый контроль | Проверка |
|---|---|---|---|
| `.env` с BOM/CRLF | первый ключ не читается | `scripts/deployment/preflight.sh` | preflight завершается ошибкой |
| пустой `ADMIN_TOKEN` | backend 503 | preflight требует непустое значение | `/api/health`, login test |
| SMTP user без password в Compose | Alertmanager crash/535 | override требует обе переменные | `docker compose config`, AM health |
| entrypoint теряет executable bit | container permission denied | preflight `--fix` + CI `bash -n` | `test -x` |
| raw backup `/var/lib/docker/volumes` | неконсистентные БД | короткая остановка writers + tar staging | restore lab |
| Mongo container name меняется | backup/restore падает | `docker compose ps -q mongo` | CI static gate |
| потерян `stalwart-etc` | домены/DKIM не восстановить | архивируются оба Stalwart volume | clean restore |
| потерян MAX `max.db` | повторная SMS-авторизация | отдельный session archive | `auth` без `--authorize` |
| Telegram блокируется с VM | потеря единственного канала | MAX + Postbox; Telegram только fallback/local watcher | тестовый P1 |
| ICMP закрыт Security Group | ложный VM-down | VM watcher проверяет TCP/443 | workstation lab |
| `YC_CONFIG_DIR` игнорируется | watcher не видит профиль | yc использует профиль пользователя | `yc config list` |
| изменился SSH host key | MITM или небезопасный bypass | `accept-new` только для первого подключения; замену сверять в console | migration gate |
| environment state попал в Git | раскрытие topology | `.deploy-state.json` удалён и ignored | repo validator |

## Перед deploy

```bash
bash scripts/deployment/preflight.sh
```

## После deploy

```bash
curl -fsS http://127.0.0.1:8001/api/health
curl -fsS http://127.0.0.1:9090/-/healthy
curl -fsS http://127.0.0.1:9093/-/healthy
curl -fsS http://127.0.0.1:9095/health
sudo docker exec msp-max-alerter python -m max_alerter.auth
```

Затем отправить контролируемый P1, проверить MAX и email, создать новый backup и выполнить test restore в чистом окружении.


## Уроки миграции 28.09.2026 (проверено на реальном переезде)

| Тема | Симптом | Системный контроль | Проверка |
|---|---|---|---|
| Новый публичный IP недостижим из целевого региона | сайт «не работает» (TCP timeout), ICMP ок | smoke-тест TCP из РФ до DNS switch; иначе пересоздать адрес в другом пуле | `curl`/`nc` с российской машины |
| Одиночная ВМ + bastion | лишняя ВМ и путаница | bastion — временный; удалять сразу после прямого доступа | `yc compute instance list` = 1 |
| Caddy-placeholder от cloud-init | 503 «provisioning» | сверять `/etc/caddy/Caddyfile` с репозиторием при деплое | `curl -I https://<domain>` |
| Caddyfile без `MSP_DOMAIN` | caddy не стартует: «server block without any key» | env/systemd override для юнита Caddy | `caddy validate` |
| restore-on-vm и раскладка артефактов | тома молча не восстановлены | класть артефакты плоско в `MIGRATION_DIR`; копировать через `sudo sh -c 'cp …'` | `ls /tmp/migration`; `du -sh` томов |
| Пустой `stalwart-data` | Stalwart в bootstrap-режиме (нет ящиков) | восстанавливать ОБА тома; конфиг хранится в RocksDB | grep «bootstrap» в логе; ящики на месте |
| restic: ключи привязаны к аккаунту/бакету | `SignatureDoesNotMatch` на новом бакете | новый access key + `restic init` при переезде аккаунта | `restic snapshots` |
| Postbox: ключ + DKIM заново | `550 identity not verified`; отправка не идёт | пересоздать API-ключ; DKIM — CNAME из консоли (→ `<selector>.dkim.pstbx.ru`), дождаться verified | тестовое письмо через SMTP |
| Stalwart-релей: креды маршрута не обновляются из .env | письма копятся молча; в очереди `535 Authentication failed` | обновить `x:MtaRoute/set` + **рестарт** Stalwart (MIGRATION_RUNBOOK §9.9) | письмо на `check-auth@verifier.port25.com` |
| Amnezia PPA после переноса | apt «is not signed» | ключ в `/etc/apt/trusted.gpg.d/`, без `signed-by` в list | `apt-get update` exit 0 |
| AWG: SG/ufw без UDP/443 | рукопожатие не проходит | gate: UDP 443 на SG + ufw allow; SSH-from-VPN правило | `awg show latest-handshakes` |
| cloud-init: IPv6-зеркала, битый NodeSource, нет unzip | apt/распаковка падают | ForceIPv4; чистить лишние apt-репозитории; доустановка утилит | `apt-get update`, `unzip -v` |
| `key.json` невалиден | yc CLI не работает | проверка JSON до автоматизации | `yc config list` |
