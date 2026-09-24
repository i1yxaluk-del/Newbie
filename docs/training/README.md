# Программа допуска Junior MSP Engineer

Допуск основан на evidence, а не на сроке работы.

## Уровни

| Уровень | Разрешено | Запрещено |
|---|---|---|
| L0 Observe | dashboards, read-only logs, документация | изменения |
| L1 Assisted | runbook при screen sharing | самостоятельный production |
| L2 Supervised | одобренный change с reviewer | firewall/backup policy/P1 commander |
| L3 Independent | Bronze P2/P3 и регулярные операции | Gold/on-call без отдельного gate |

## Маршрут

1. [`JUNIOR_OPERATIONS_GUIDE.md`](JUNIOR_OPERATIONS_GUIDE.md) — как читать scripts/runbooks.
2. `week_01.md`…`week_12.md` — теория и базовая практика.
3. [`DEPLOYMENT_MIGRATION_LABS.md`](DEPLOYMENT_MIGRATION_LABS.md) — реальные уроки deployment.
4. [`../runbooks/README.md`](../runbooks/README.md) — incident response.
5. Итоговый Bronze exam.

## Обязательные навыки L2

- preflight и чтение Compose config без вывода секретов;
- backup Mongo и stateful services с корректным writer handling;
- clean-room restore и RTO/RPO evidence;
- MAX session transfer без автоматической SMS;
- диагностика Postbox SMTP 535;
- TCP/443 VM health вместо вывода по одному ICMP;
- SSH host-key verification;
- change/rollback/client update.

Провал security-критерия означает повтор упражнения.
