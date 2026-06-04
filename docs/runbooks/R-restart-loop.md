# R-restart-loop · Рестарт-луп контейнера

| | |
|---|---|
| **Alert** | `ContainerRestartLoop` |
| **Severity** | P2 |
| **Expression** | `increase(container_start_time_seconds[15m]) > 2` for 0m |
| **Summary** | Контейнер перезапускается >2 раз за 15 минут |

## Диагностика

1. `docker logs <name> --tail 200` — причина crash
2. `docker inspect <name> --format='{{.State.ExitCode}}'` — exit code
3. `docker inspect <name> --format='{{.State.Error}}'`
4. `free -h` — достаточно ли RAM

## Устранение

1. Exit 137 = OOM: увеличить memory limit
2. Exit 1 = app error: читать лог, исправить config
3. Exit 132 = segfault: проверить image version
4. Временно: `docker compose stop <service>` чтобы не спамил
5. Исправить root cause, затем `docker compose up -d <service>`
