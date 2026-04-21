# Deployment Guide

> Развёртывание web-части MSPShield (лендинг + API) в продакшен.
> Инфраструктура MSP для клиентов — см. `technical/`.

## Варианты деплоя

| Вариант | Плюсы | Минусы | Кому подойдёт |
|---|---|---|---|
| Emergent (нативный) | 1 клик, автомасштаб, SSL | Привязка к платформе | MVP, первые 6 месяцев |
| VPS + Docker Compose | Полный контроль | Ручной SSL, обновления | После 50+ заявок/месяц |
| Yandex Cloud (Serverless) | Маштабируется, РФ | Vendor lock-in | Крупный поток |

---

## Вариант 1. Docker Compose (VPS 2 CPU / 2 ГБ)

### 1.1 Подготовка

```bash
# Ubuntu 22.04
apt update && apt install -y docker.io docker-compose-v2 nginx certbot python3-certbot-nginx
```

### 1.2 `docker-compose.yml`

```yaml
services:
  mongo:
    image: mongo:7
    volumes: [mongo-data:/data/db]
    restart: unless-stopped

  backend:
    build: ./backend
    environment:
      MONGO_URL: mongodb://mongo:27017
      DB_NAME: mspshield
      ADMIN_TOKEN: ${ADMIN_TOKEN}
      TG_BOT_TOKEN: ${TG_BOT_TOKEN}
      TG_CHAT_ID: ${TG_CHAT_ID}
      CORS_ORIGINS: https://mspshield.ru
    depends_on: [mongo]
    ports: ["127.0.0.1:8001:8001"]
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      args:
        REACT_APP_BACKEND_URL: https://mspshield.ru
    ports: ["127.0.0.1:3000:80"]
    restart: unless-stopped

volumes:
  mongo-data:
```

### 1.3 Nginx reverse-proxy (основные правила)

```nginx
server {
  listen 443 ssl http2;
  server_name mspshield.ru;
  ssl_certificate     /etc/letsencrypt/live/mspshield.ru/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/mspshield.ru/privkey.pem;

  location /api/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  location / {
    proxy_pass http://127.0.0.1:3000;
  }
}
```

### 1.4 Первичный запуск

```bash
git clone <repo> /opt/mspshield && cd /opt/mspshield
cat > .env <<EOF
ADMIN_TOKEN=$(openssl rand -hex 32)
TG_BOT_TOKEN=...
TG_CHAT_ID=...
EOF

docker compose up -d --build
certbot --nginx -d mspshield.ru
```

---

## Вариант 2. Emergent (быстрый старт)

1. В платформе Emergent: `Deploy` → выбрать окружение prod.
2. В Secrets добавить: `ADMIN_TOKEN`, `TG_BOT_TOKEN`, `TG_CHAT_ID`.
3. `REACT_APP_BACKEND_URL` проставляется автоматически.
4. Домен привязывается через `Custom Domain`.

---

## Проверка после деплоя

```bash
curl -sf https://mspshield.ru/api/health | jq .
curl -sf -H "X-Admin-Token: $ADMIN_TOKEN" https://mspshield.ru/api/stats | jq .
```

## Резервное копирование MongoDB

Ежедневно в 03:00 через systemd timer:

```bash
mongodump --uri="mongodb://mongo:27017/mspshield" --out=/var/backups/mongo/$(date +%F)
restic -r s3:s3.yandexcloud.net/mspshield-backups backup /var/backups/mongo/$(date +%F)
```

## Мониторинг самого себя

Добавить экспортеры mongodb и nginx в свой же Prometheus:
- `mongodb_exporter` — состояние БД
- `nginx-exporter` — RPS / 5xx
- `blackbox_exporter` — доступность `/api/health` извне

**«Сапожник в сапогах» — одно из главных преимуществ перед конкурентами.**
