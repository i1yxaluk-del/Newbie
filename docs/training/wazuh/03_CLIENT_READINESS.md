# 3. Расширенный стенд и будущий клиент

[← Курс](README.md) · [Далее: экзамен](04_EXAM.md)

## Матрица возможностей

| Возможность | Уже в lab | Следующий проверяемый шаг |
|---|---|---|
| JSON decoding/custom rules | Да, 4 synthetic scenarios | Новые fixtures, позитивный и негативный тест через logtest |
| FIM | Да, только учебный каталог | Изолированный agent, scoped paths, baseline/noise/permissions |
| SCA/inventory | Manager container | Поддерживаемый agent на отдельном Linux/Windows endpoint; policy по реальной ОС |
| Vulnerability detection | Config включён | Feed, inventory, реальные результаты и ограничения платформы |
| Windows EventChannel/Sysmon | Нет | Лицензированный тестовый Windows, отдельное разрешение, audit policy, небольшой scope |
| Linux auditd | Нет на host | Отдельный тестовый endpoint, производительность, проверка событий |
| Docker events | Отдельная интеграция не настроена | Оценить права на socket и blast radius; не монтировать host Docker socket в manager автоматически |
| Active Response | Не активирован | Только отдельный disposable endpoint, безопасное действие, разрешение, rollback и наблюдатель |
| Kaspersky/EDR | Не установлен | Лицензии, совместимость, отдельный проект интеграции; Wazuh не включает продукт вендора |

## До подключения учебного агента

Наставник выбирает отдельный endpoint и данные, выдаёт персональные роли, проверяет версии, TCP-маршрут и TLS/enrollment. На текущем manager enrollment `1515` выключен: не открывать его всем ради удобства. После подключения проверить уникальный agent ID, labels группы, inventory и test event. Manager ID `000` не выдавать за успех подключения.

## До клиентского внедрения

1. Подписанный scope: endpoints, данные/ПДн, регионы и retention, ответственные, рабочее окно, допустимые действия.
2. Права: отдельные учётки/RBAC, tenant isolation, secrets/recovery, аудит доступа. Учебный `admin` не переносится клиенту.
3. Мощность: EPS, storage/day, число агентов, сроки хранения, нагрузка inventory/feed, реальная стоимость. 4 vCPU/8 GiB/50 GB — quickstart-ориентир, не универсальный production sizing.
4. Сбор и реакция: правила, шум/ложные срабатывания, резервный канал, кто подтверждает и диагностирует. Wazuh level не равен SLA priority.
5. Backup/DR: конфигурация, certificates/keys, indexer state, восстановление и проверка поиска. Наличие контейнеров и green не является evidence восстановления.
6. Приёмка: end-to-end событие от настоящего endpoint, корректное правило/индекс/доступ, контроль потерь, документация и shadowing Junior.

Регламенты PCI/GDPR/HIPAA/NIST в интерфейсе — классификация и панели, а не сертификат соответствия РФ/152-ФЗ. Gold требует [capacity gate](../../../commercial/PRICING.md). Сначала [экзамен](04_EXAM.md), затем ограниченный production scope под reviewer.
