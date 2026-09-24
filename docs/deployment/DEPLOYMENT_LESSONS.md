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
