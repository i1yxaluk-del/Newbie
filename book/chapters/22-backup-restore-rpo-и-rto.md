# 22. Резервная копия, восстановление, RPO и RTO

> **Учебная ситуация.** Резервная копия job зелёный, но никто не знает, можно ли восстановить сервис.

## Главное

Резервная копия — копия определённого набора данных; snapshot — зафиксированное состояние repository. Ни одно слово не означает автоматически consistency.

RPO измеряет допустимую потерю по времени, RTO — время восстановления сервиса. Цель становится доказанной только в упражнении.

MSPShield требует Mongo dump, Vaultwarden data, оба Stalwart volumes и MAX session. Ключи repository и восстановление секрет доступаs — отдельная зависимость.

## Как это работает

Capture выбирает согласованную точку Mongo и сохранённые данныеful services, restic сохраняет encrypted snapshot, `restic check` проверяет repository structure, восстановление materializes files. Затем приложение должно стартовать и пройти приёмка. Только последняя часть доказывает recoverability.

## Пример

```bash
sudo bash /opt/restic-scripts/резервная копия.sh
source /etc/restic/env.sh
restic snapshots --latest 1
restic check
restic восстановление latest --target /tmp/восстановление-test
```

## Практикум

1. Сделайте snapshot.
2. Восстановите в clean target, не поверх production.
3. Поднимите сервис и измерьте RPO/RTO.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Snapshot есть, размер 0 | capture path неверен. |
| Repository доступен, password потерян | восстановление невозможен. |

## Источники проекта

- [migration/restic-резервная копия.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/migration/restic-резервная копия.sh)
- [docs/deployment/disaster_recovery.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/disaster_recovery.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

