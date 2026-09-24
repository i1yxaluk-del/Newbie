# Vaultwarden: организация, коллекции и импорт секретов

Как централизованно вести пароли сотрудников в self-hosted Vaultwarden (`vault.msp-claude.online`).

## 1. Готовность (проверено на инсталляции)

| Параметр | Значение |
|---|---|
| Vaultwarden | 1.36.0 (организации/коллекции поддерживаются; лицензия Bitwarden не нужна) |
| `INVITATIONS_ALLOWED` | `true` |
| `SIGNUPS_ALLOWED` | `false` (только по приглашению) |
| SMTP (инвайты) | Postbox `postbox.cloud.yandex.net:465`, креды = API-ключ со scope `yc.postbox.send` |
| Админ-панель | `/admin` (ADMIN_TOKEN) |

## 2. Порядок: вариант «через организацию»

1. Войти в веб-сейф аккаунтом, который будет **Owner**.
2. **New organization** — имя, billing email, план (в self-hosted платно не требуется).
3. **Collections** — создать логические группы (напр. «Инфраструктура», «Почта», «CRM», «Мониторинг»).
4. **Members → Invite user** — e-mail + роль + доступ к коллекциям. Письмо уходит по SMTP; иначе — скопировать ссылку-приглашение вручную.
5. **Tools → Import data** — формат **Bitwarden (json)**, файл импорта, **destination = организация/коллекция** (не личный сейф).
6. **Назначить доступ** — Collections → коллекция → участники с правами **View / Edit / Manage**.

## 3. Роли и права

| Роль / право | Что даёт |
|---|---|
| Owner | всё: участники, коллекции, биллинг, удаление организации |
| Admin | управление участниками/коллекциями; в админ-консоли видит все коллекции |
| User | видит только выданные коллекции |
| View / Edit / Manage | просмотр / изменение / управление доступом к коллекции |

> Admin/Owner видят все коллекции в админ-консоли организации, но в личном сейфе — только те, к которым есть явный доступ.

## 4. Как собрать импорт-файл для Vaultwarden (ключи/логины)

Формат — **Bitwarden JSON (unencrypted)**:

```json
{
  "encrypted": false,
  "folders": [ { "id": "<uuid>", "name": "Monitoring" } ],
  "items": [
    {
      "id": "<uuid>",
      "organizationId": null,
      "folderId": "<uuid>",
      "type": 1,
      "reprompt": 0,
      "name": "Monitoring · Grafana admin",
      "notes": "Админ Grafana (мониторинг).",
      "favorite": false,
      "login": {
        "uris": [ { "match": null, "uri": "https://mon.msp-claude.online" } ],
        "username": "admin",
        "password": "<secret>",
        "totp": null
      },
      "collectionIds": null
    }
  ]
}
```

- `type: 1` — логин, `type: 2` — защищённая заметка (`"secureNote": {"type": 0}`).
- `encrypted: false` — файл в открытом виде (шифрование происходит при импорте).
- `folderId`/`collectionIds` — можно оставить `null`/локальные; **целевую коллекцию выбирают в UI при импорте**.

Генерация из `.env` (пример — мониторинг):

```python
import json, uuid, subprocess
def env(p):
    d = {}
    for l in subprocess.check_output(["sudo","cat",p]).decode(errors="replace").splitlines():
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, v = l.split("=", 1); d[k.strip()] = v.strip()
    return d

mo = env("/opt/msp/Newbie/deploy/yandex/monitoring/.env")
folder = {"id": str(uuid.uuid4()), "name": "Monitoring"}
item = {
    "id": str(uuid.uuid4()), "organizationId": None, "folderId": folder["id"],
    "type": 1, "reprompt": 0, "name": "Monitoring · Grafana admin", "notes": "",
    "favorite": False,
    "login": {"uris": [{"match": None, "uri": "https://mon.msp-claude.online"}],
              "username": mo["GRAFANA_ADMIN_USER"], "password": mo["GRAFANA_ADMIN_PASSWORD"], "totp": None},
    "collectionIds": None,
}
json.dump({"encrypted": False, "folders": [folder], "items": [item]},
          open("vaultwarden-import-monitoring.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
```

Готовый пример (6 записей): Grafana admin, Postbox SMTP (alerts), Alertmanager webhook token, Telegram bot, MAX alerter (заметка), Grafana SMTP (заметка).

**Импорт:** Tools → Import data → **Bitwarden (json)** → destination = организация/коллекция (для шеринга с `alert@`) либо личный сейф.
**Безопасность:** файл содержит секреты в открытом виде — импортировать из доверенного клиента и сразу удалить; в git не коммитить (`.env`/секреты исключены `.gitignore`).

## 5. Нюансы

- Master-пароль невосстановим — держать **двух Owner** (или emergency-access).
- Удаление участника отзывает доступ к коллекциям; уже скопированное им в личный сейф остаётся.
- Включить 2FA; при желании ограничить создание организаций (`ORG_CREATION_USERS`).
- Bitwarden-клиенты могут показывать баннер об апгрейде — косметика, организации в Vaultwarden работают.
