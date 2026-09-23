# Технические пакеты MSPShield

Главное правило: тариф определяется не только количеством серверов, а фактическим периметром, критичностью, объёмом ручной работы и рабочим окном.

| Пакет | Статус | База | Ручной лимит | Основной стек |
|---|---|---:|---:|---|
| Bronze Pilot | активен | 25 000 ₽ | 2 ч инженера/мес | Prometheus, Grafana, Alertmanager, restic, AmneziaWG |
| Silver Managed | ограниченно | 50 000 ₽ | 4 ч инженера/мес | Bronze + Loki + Ansible + AD/DNS/GPO; Puppet только по обоснованию |
| Gold Future | закрыт до gate | 120 000 ₽ | индивидуально | Silver + Wazuh; EDR только с лицензиями клиента |

## Маршрут Junior

1. Сначала прочитать [`../docs/training/README.md`](../docs/training/README.md).
2. Для задачи открыть мастер-гайд тарифа.
3. Найти связанный runbook.
4. Выполнить изменение на тестовом стенде.
5. Получить подтверждение owner/senior на production.
6. Зафиксировать команду, результат и rollback в карточке.

Никогда не копируй команду из документа вслепую. Сначала проверь hostname, tenant, путь, ожидаемый результат и способ отката.

## Мастер-гайды

- [`1_Bronze/Bronze.md`](1_Bronze/Bronze.md)
- [`2_Silver/Silver.md`](2_Silver/Silver.md)
- [`3_Gold/Gold.md`](3_Gold/Gold.md)
- [`BUSINESS_MODEL.md`](BUSINESS_MODEL.md)
- [`SCALING.md`](SCALING.md)
