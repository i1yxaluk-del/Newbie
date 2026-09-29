# 24. Secrets, Vaultwarden и доступ

> **Учебная ситуация.** Новый администратор должен получить минимальный доступ и потерять его при offboarding.

Предыдущая глава: [глава 23](./23-миграция-и-disaster-recovery.md).

## Модель, которую нужно построить

Secret даёт возможность действовать от имени identity. Его lifecycle: создать, передать, использовать, ротировать, отозвать, уничтожить.

Vaultwarden хранит значения и sharing; Kaiten хранит задачу и факт выдачи, но не пароль. Git содержит `.env.example`, а не `.env`.

MFA снижает риск украденного пароля, но recovery codes сами являются secrets. Break-glass доступ должен быть ограничен и проверяем.

## Термины в рабочем смысле

### secret lifecycle

Создание, хранение, выдача, использование, rotation, revocation и уничтожение credential. Пропуск offboarding оставляет orphan access.

### least privilege

Identity получает только actions/resources/time, необходимые задаче. Удобство не является доказательством необходимости admin role.

### evidence

Минимальный проверяемый артефакт: timestamp, exit code, hash, запрос/ответ, metric или подписанный документ. Скриншот зелёной панели без target и времени — слабое evidence.

## Что происходит внутри

Secret появляется при generation и должен иметь owner/purpose/expiry. Vault sharing выдаёт доступ identity; запись в access matrix объясняет основание. При offboarding сначала revoke, затем rotation shared credentials, затем проверка logs. Удаление карточки пользователя без rotation может оставить ранее скопированный секрет рабочим.

## Разобранный пример

```bash
umask 077
openssl rand -hex 32 > /tmp/token
chmod 600 deploy/yandex/monitoring/.env
git status --ignored --short
```

### Как читать пример

- `umask 077` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `openssl rand -hex 32 > /tmp/token` — `openssl rand -hex 32` получает 32 random bytes и печатает 64 hex-символа; вывод нужно сразу хранить защищённо.
- `chmod 600 deploy/yandex/monitoring/.env` — `chmod` изменяет permission bits; он не меняет владельца и не отзывает уже скопированный secret.
- `git status --ignored --short` — Git-команда читает или изменяет working tree/index/refs; перед mutation сравните `status` и `diff`.

## Практикум

1. Создайте collection для test client.
2. Выдайте Junior один credential и проверьте границу.
3. Отзовите доступ и ротируйте secret.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Секрет в ticket | Это сужает область поиска, но не доказывает единственную причину | удалить/ротировать, не просто скрыть сообщение. |
| Compose config показал secret | Это сужает область поиска, но не доказывает единственную причину | не прикладывать полный вывод. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Новый администратор должен получить минимальный доступ и потерять его при offboarding.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `secret lifecycle` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `least privilege` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `evidence` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Секрет в ticket» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/deployment/secrets_management.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/secrets_management.md)
- [docs/deployment/VAULTWARDEN_ORG_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/VAULTWARDEN_ORG_RUNBOOK.md)

- [Русскоязычный видеопоиск: Secrets, Vaultwarden и доступ](https://www.youtube.com/results?search_query=Secrets%2C+Vaultwarden+%D0%B8+%D0%B4%D0%BE%D1%81%D1%82%D1%83%D0%BF+%D0%BD%D0%B0+%D1%80%D1%83%D1%81%D1%81%D0%BA%D0%BE%D0%BC)

## Условие перехода

Глава завершена, если вы можете связно объяснить `secret lifecycle`, `least privilege`, `evidence`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
