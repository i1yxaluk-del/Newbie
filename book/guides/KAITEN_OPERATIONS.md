# Kaiten для двухчленной MSP-команды

На пилоте Kaiten используют 2–3 человека, поэтому исходная модель не должна зависеть от платной лицензии. Kaiten — интерфейс управления работой; договор, Git, Vaultwarden и monitoring остаются отдельными source of truth.

## Пространства и доски

Минимальный набор:

- `Sales` — New → Qualified → Discovery → Proposal → Contract → Won/Lost/Waitlist;
- `Client onboarding` — доступы, inventory, backup baseline, monitoring, acceptance;
- `Operations` — Ready → In progress → Review → Done;
- `Incidents and changes` — отдельные типы карточек и service class.

Не создавайте отдельную доску на каждый мелкий процесс: навигация станет дороже работы.

## Карточка

Карточка обязана отвечать: клиент, owner, тип работы, priority/service class, deadline или окно change, acceptance criteria, риск и ссылка на evidence. Секреты и персональные данные в карточку не вставляются — только ссылка на Vaultwarden или разрешённый документ.

## WIP и capacity

Для двух человек разумный стартовый лимит — по одной основной работе на человека плюс отдельный expedite lane для подтверждённого incident. Лимит меняется по данным cycle time и очереди, а не по желанию взять больше клиентов. Gold не попадает в Contract до capacity check.

## Автоматизации

Безопасные примеры: назначить label по типу, уведомить о просрочке, создать checklist из template. Опасные примеры: автоматически закрыть incident, удалить карточку, обещать SLA или менять приоритет без owner. Сначала правило тестируется на sandbox-board.

## Метрики

- lead time от commitment до delivery;
- cycle time активной работы;
- blocked time;
- WIP и возраст незавершённых карточек;
- throughput за период;
- доля срочной работы.

Velocity без общего определения размера не сравнивается между командами.

## Практикум

1. Создайте тестовое пространство и четыре доски.
2. Настройте шаблоны incident, change, onboarding и discovery.
3. Установите WIP-лимит и намеренно превысьте его, чтобы увидеть сигнал.
4. Проведите одну заявку через Sales → onboarding → operations.
5. Экспортируйте недельные данные и объясните узкое место.

## Видео

- [Работа с карточками Kaiten](https://www.youtube.com/watch?v=mXpJ9frcFY4) — официальный ввод.
- [Автоматизации в Kaiten](https://www.youtube.com/watch?v=QfYok88UGbA) — официальный разбор.
- [WIP-лимиты и классы обслуживания](https://www.youtube.com/watch?v=LdguvbxPRR8) — процессная модель, которую нужно перенести в Kaiten.

Ролик засчитывается только вместе с настроенной тестовой доской и разобранной ошибкой процесса.
