# role: `nginx`

> Реверс-прокси + TLS-терминатор на landing-VM. `mspshield.ru` → FastAPI-backend (uvicorn :8001) + статика CRA build.

## Что делает

1. Ставит `nginx-core`
2. Копирует `deploy/nginx/mspshield.conf` → `/etc/nginx/sites-available/mspshield.conf` + symlink в `sites-enabled/`
3. Удаляет дефолтный `default` симлинк
4. Certbot получает LE-серт (см. role-var `nginx_certbot_email`, `nginx_server_name`)
5. `nginx -t` + reload

## Переменные

- `nginx_server_name` (default `mspshield.ru`)
- `nginx_certbot_email` (required)
- `nginx_backend_upstream` (default `http://127.0.0.1:8001`)
- `nginx_static_root` (default `/var/www/mspshield`)

## Зависимости

- `certbot` пакет + `python3-certbot-nginx` ставятся этой же ролью.
- `deploy/nginx/mspshield.conf` уже есть в репо — template'ится через `ansible.builtin.template`, подставляются `{{ nginx_server_name }}`, `{{ nginx_backend_upstream }}`.

## Где test'ить

`ansible-playbook site.yml --limit landing --tags nginx --check` — идемпотентный check без апплая.
