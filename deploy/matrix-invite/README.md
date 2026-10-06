# Matrix Invite Portal (MSPShield)

Отдельный портал приглашений для Matrix: админ создаёт ссылку (`/i/<token>`),
гость сам выбирает логин и пароль — аккаунт создаётся в Synapse через Admin API.
Публичная регистрация остаётся выключенной; в приложении нужно выбирать «Войти»,
а не «Создать аккаунт».

- Хостинг на VM: `/opt/matrix-invite` (systemd `matrix-invite.service`, 127.0.0.1:8896).
- Домен: **https://names.msp-claude.online** (свободный A-рекорд; Caddy → 8896).
- Админка: `https://names.msp-claude.online/admin?token=<ADMIN_TOKEN>`
  (токен — в `~/msp-deploy-secrets.txt` [MATRIX-INVITE] и в `/opt/matrix-invite/.env`).
- Переменные окружения (`.env`): ADMIN_TOKEN, MATRIX_DOMAIN, SYNAPSE_URL,
  SYNAPSE_ADMIN_TOKEN (access-token admin-а Synapse, создаётся при деплое),
  ELEMENT_URL, INVITE_BASE.
- Регистрация гостя: `POST /i/<token>/register` → проверка занятости логина →
  Synapse Admin API `PUT /_synapse/admin/v2/users/<mxid>`; приглашение одноразовое.
- Удаление аккаунта из админки: `POST /admin/accounts/deactivate` (deactivate + erase).
- `/welcome/<token>` редиректит на `/i/<token>`.

## Проверка

```bash
curl -s https://names.msp-claude.online/health
```
