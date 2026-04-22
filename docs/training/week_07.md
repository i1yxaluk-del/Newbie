# Week 7 · Active Directory + GPO

## Цель

Разобраться с Microsoft AD на уровне достаточном для Silver/Gold
клиентов. Диагностировать типичные проблемы.

## Задачи

- [ ] Поднять тестовый Windows Server с AD DS на VM (demo license
      180 дней).
- [ ] Пройти full R-05 (AD replication failure) на демо-стенде.
- [ ] Прочитать с owner `docs/runbooks/R-05.md` и обсудить каждую команду.
- [ ] Создать GPO для disable USB storage, применить, проверить.

## Production

- [ ] Под supervision — password reset через AD у Silver-клиента.
- [ ] Проверить `ad_replication_lag` metric по всем Silver/Gold.

## Read

- [Microsoft Docs: Troubleshoot AD replication](https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/troubleshoot-active-directory-replication-problems).
- `dcdiag /?` и `repadmin /?`.

## Check-in

1. Что проверяет `dcdiag` (минимум 3 теста)?
2. FSMO роли — что это и как посмотреть?
3. Типичная причина AD replication lag?

## DoD

- Поднял тестовый AD-домен самостоятельно.
- Может пройти R-05 от первого шага до последнего.
- Под supervision выполнил production AD-операцию.
