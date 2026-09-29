# 24. Secrets, Vaultwarden и доступ

> **Учебная ситуация.** Новый администратор должен получить минимальный доступ и потерять его при завершение обслуживания.

## Главное

Secret даёт возможность действовать от имени identity. Его lifecycle: создать, передать, использовать, ротировать, отозвать, уничтожить.

Vaultwarden хранит значения и sharing; Kaiten хранит задачу и факт выдачи, но не пароль. Git содержит `.env.example`, а не `.env`.

MFA снижает риск украденного пароля, но recovery codes сами являются secrets. Break-glass доступ должен быть ограничен и проверяем.

## Как это работает

Secret появляется при generation и должен иметь владелец/purpose/expiry. Vault sharing выдаёт доступ identity; запись в доступы matrix объясняет основание. При завершение обслуживания сначала revoke, затем замена shared секрет доступаs, затем проверка logs. Удаление карточки пользователя без замена может оставить ранее скопированный секрет рабочим.

## Пример

```bash
umask 077
openssl rand -hex 32 > /tmp/token
chmod 600 развёртывание/yandex/monitoring/.env
git status --ignored --short
```

## Практикум

1. Создайте collection для test client.
2. Выдайте Junior один секрет доступа и проверьте границу.
3. Отзовите доступ и ротируйте secret.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Секрет в ticket | удалить/ротировать, не просто скрыть сообщение. |
| Compose config показал secret | не прикладывать полный вывод. |

## Источники проекта

- [docs/развёртываниеment/secrets_management.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/secrets_management.md)
- [docs/развёртываниеment/VAULTWARDEN_ORG_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/VAULTWARDEN_ORG_RUNBOOK.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

