# 🌱 Жизненный цикл сайта MSPShield — для одного человека

> Аудитория: **владелец без опыта деплоя** (раньше публиковал только статические HTML-странички).
> Цель: за один вечер развернуть сайт, а дальше — уверенно им управлять.

Документ собирает в одном месте **всё, что происходит с сайтом после написания кода**:

1. **Развёртывание** — от «купил VM» до «сайт виден из интернета».
2. **Ведение** — мониторинг, куда падают заявки, где их анализировать.
3. **Изменение** — как поменять цифры, удалить блок, заменить текст без страха что-то сломать.
4. **Траблшутинг** — что делать, когда «сайт не открывается», «форма не отправляется», «цены неправильные».

Все команды проверены в версии проекта **v4.2** (после упрощения лендинга до 9 секций).

---

## 0. Что из себя представляет «сайт»

Сайт = **3 контейнера + 1 файл конфигурации nginx**, живущие на одной виртуалке в Yandex Cloud:

| Компонент | Что делает | Порт | Где код |
|---|---|---|---|
| **frontend** (nginx + static build) | отдаёт React-страницу посетителю | 80 / 443 | `frontend/` |
| **backend** (FastAPI + Python) | принимает заявки с формы, пишет в Mongo, отдаёт `/metrics` | 8001 (только внутрь) | `backend/` |
| **MongoDB** | хранит заявки | 27017 (только внутрь) | `deploy/docker-compose.yml` |

И над ними:

- **nginx** на хосте VM — единственный, кто смотрит в интернет, перекидывает `/` на frontend-контейнер и `/api/*` на backend.
- **Let's Encrypt сертификат** — бесплатный, обновляется сам.
- **Prometheus + Grafana + Alertmanager** — отдельная VM (мониторинг), опционально. Для старта лендинга **не обязательны**.

Визуально:

```
интернет → DNS (mspshield.ru) → nginx(443) → ┬─ frontend (React static)
                                             └─ backend (FastAPI) → MongoDB
                                                    │
                                                    └─ POST в Telegram (заявка)
```

---

## 1. Первый деплой — от нуля до публичного сайта

**Результат:** `https://mspshield.ru` открывается в браузере, форма отправляется, заявка приходит в Telegram.
**Время:** 2–3 часа первый раз (половина — ожидание DNS и Let's Encrypt).

> Полный командный раннер живёт в `docs/deployment/landing_production.md`. Здесь — **его краткий пересказ с пояснениями, зачем каждый шаг**.

### 1.1 Что нужно подготовить заранее (30 мин)

- [ ] Зарегистрирован домен **mspshield.ru** (или любой другой — дальше везде подставь свой).
- [ ] Создан аккаунт **Yandex Cloud**, привязана карта, включён хотя бы один платёжный аккаунт ([console.cloud.yandex.ru](https://console.cloud.yandex.ru)).
- [ ] Скачан `yc` CLI и выполнен `yc init` (это положит токен в `~/.config/yandex-cloud/config.yaml`).
- [ ] Создан **Telegram-бот** через [@BotFather](https://t.me/BotFather) → получен `TELEGRAM_BOT_TOKEN`.
- [ ] Создан Telegram-чат (или использован личный) и узнан его **chat_id** (боту послать `/start`, потом открыть `https://api.telegram.org/bot<TOKEN>/getUpdates`).

### 1.2 Поднять инфру (Terraform, 15 мин)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars  # отредактировать: folder_id, cloud_id, zone
terraform init
terraform plan                # прочитать внимательно — покажет, что создаст
terraform apply               # подтвердить yes
```

**Что создастся:** 2 VM (landing + bastion), сеть, security-group, SSH-ключи. `terraform output` покажет публичный IP лендинга — **он понадобится для DNS**.

⚠️ **Если `terraform apply` упал** — читай секцию «Траблшутинг: Terraform» в конце документа. Не паникуй, ничего не сломалось.

### 1.3 Настроить DNS (10 мин + ожидание до 1 ч)

У регистратора домена:

```
A    mspshield.ru        → <IP из terraform output>
A    www.mspshield.ru    → <тот же IP>
```

Проверить, что DNS поехал:

```bash
dig +short mspshield.ru          # должен вернуть твой IP
# или через публичный резолвер:
dig @8.8.8.8 +short mspshield.ru
```

Пока DNS не зарезолвился на всех резолверах — **не запускай certbot**, он не сможет выпустить сертификат.

### 1.4 WireGuard между тобой и bastion'ом (15 мин)

Bastion — это «дверь» в приватную сеть. Через него ты заходишь на landing-VM и, позже, на VM клиентов.

```bash
# На своём ноутбуке (или где запускаешь Ansible):
ssh ubuntu@<bastion-IP>                       # первый раз по публичному ключу из terraform
sudo bash /root/wg_bootstrap.sh               # поднимет WG-сервер
sudo bash /root/tenant_add.sh owner           # выдаст owner.conf — импортировать в WireGuard app
```

После импорта конфига в WireGuard клиент (mac/win/linux/ios) — у тебя появляется приватный IP `10.10.0.x` и ты **видишь landing-VM напрямую** через его внутренний IP.

### 1.5 Ansible раскатывает landing-стек (20 мин)

```bash
cd technical/0_Common/ansible
# Проверить что видишь хосты:
ansible -i inventory/prod.yml all -m ping

# Раскатать лендинг (nginx + backend + mongo):
ansible-playbook -i inventory/prod.yml playbooks/site.yml --limit landing
```

⚠️ **Важно (известно в v4.2):** `site.yml` ссылается на роли `nginx`, `fastapi_backend`, `mongo` и др. — **эти роли ещё не имплементированы** как отдельные директории `roles/*`. В текущей версии раскатка landing'а делается **вручную по `docs/deployment/landing_production.md`** (docker compose up), а Ansible пока применяется только для **патчинга** уже работающей VM (`playbooks/patch_nondisruptive.yml`).

Если ты идёшь в прод первый раз — **выбирай путь из `docs/deployment/landing_production.md` шаг за шагом**. Он ручной, но **реально работает сегодня**.

### 1.6 Docker-стек на landing-VM (ручной путь, 15 мин)

Через WireGuard зайти на landing-VM:

```bash
ssh ubuntu@10.10.0.2                          # внутренний IP лендинга
git clone https://github.com/i1yxaluk-del/Newbie.git mspshield
cd mspshield/deploy

# Скопировать примеры конфигов и заполнить секреты:
cp ../backend/.env.example ../backend/.env
nano ../backend/.env                          # заполнить MONGO_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ADMIN_TOKEN

# Frontend env:
echo "REACT_APP_BACKEND_URL=https://mspshield.ru" > ../frontend/.env

docker compose up -d --build
docker compose ps                             # должно показать 3 сервиса Up
docker compose logs backend | tail -20        # без ERROR
```

### 1.7 Nginx + Let's Encrypt на хосте VM (20 мин)

```bash
sudo apt install -y nginx-full certbot python3-certbot-nginx
sudo cp /home/ubuntu/mspshield/deploy/nginx/mspshield.conf /etc/nginx/sites-available/mspshield
sudo ln -s /etc/nginx/sites-available/mspshield /etc/nginx/sites-enabled/

# ВАЖНО: certbot ДО nginx -t (потому что в конфиге уже прописаны пути к сертификату)
sudo certbot --nginx -d mspshield.ru -d www.mspshield.ru --agree-tos -m you@example.com

sudo nginx -t && sudo systemctl reload nginx
```

После этого `https://mspshield.ru` **открывается из интернета**.
Certbot настраивает автообновление сертификата (`systemctl list-timers | grep certbot`).

### 1.8 Smoke-тест — работает ли всё

Из своего браузера / терминала (не с landing-VM):

```bash
# 1. HTTPS + главная:
curl -I https://mspshield.ru | head -3
# Ожидаем HTTP/2 200

# 2. API здоровья:
curl https://mspshield.ru/api/health
# Ожидаем {"status": "ok"}

# 3. Форма — отправка заявки:
curl -X POST https://mspshield.ru/api/leads \
  -H 'Content-Type: application/json' \
  -d '{"company":"Test","contact":"Ivan","phone_or_email":"test@example.com","tariff":"Silver","consent":true,"website":""}'
# Ожидаем {"ok": true, "id": "..."}

# 4. Заявка пришла в Telegram? (проверить чат глазами)

# 5. Админка — список заявок:
curl -H "X-Admin-Token: $(grep ADMIN_TOKEN backend/.env | cut -d= -f2)" \
     https://mspshield.ru/api/admin/leads | jq .
```

Если все 5 прошли — **лендинг в проде**.

---

## 2. Ведение сайта

### 2.1 Где живут заявки

Когда посетитель нажимает **«Отправить заявку»**, происходит **3 параллельных действия**:

1. **POST /api/leads** → FastAPI пишет документ в коллекцию **`leads`** в MongoDB.
2. FastAPI делает **POST в Telegram Bot API** → уведомление прилетает в твой чат сразу.
3. FastAPI инкрементит счётчик в Prometheus (`mspshield_leads_total`) — для статистики.

**Источник истины = MongoDB**. Telegram — это «push» (если прошляпишь — не страшно, всё хранится).

#### Посмотреть заявки «глазами»

Способ А — через `curl` (быстро, 10 секунд):

```bash
ssh ubuntu@10.10.0.2
curl -H "X-Admin-Token: $ADMIN_TOKEN" http://localhost:8001/api/admin/leads | jq .
```

Способ Б — через `mongosh` (для нестандартных выборок):

```bash
ssh ubuntu@10.10.0.2
docker exec -it deploy-mongo-1 mongosh mspshield

> db.leads.find().sort({created_at: -1}).limit(10).pretty()
> db.leads.countDocuments()
> db.leads.countDocuments({created_at: {$gte: ISODate("2026-01-01")}})
> db.leads.aggregate([{$group: {_id: "$tariff", count: {$sum: 1}}}])
```

Способ В — **простая админка** (в планах Этапа 4, спринт 3): https://mspshield.ru/admin — логин `admin` + `ADMIN_TOKEN`. Пока не реализована, используй A/Б.

#### Где их анализировать

| Метрика | Где смотреть | Как часто |
|---|---|---|
| «Сколько заявок за неделю?» | `db.leads.countDocuments({created_at: {$gte: ISODate(...)}})` | Понедельник |
| «Откуда приходят — Bronze / Silver / Gold?» | `$group by tariff` | Раз в месяц |
| «Сколько конверсия из заявки → звонок?» | Статус поле `status` (`new`, `called`, `booked`, `won`, `lost`) | После каждого ответа |
| «График заявок по дням» | Grafana dashboard «MSPShield leads» (если Prometheus стоит) | Ежедневно |

Поле `status` меняется вручную через `PATCH /api/admin/leads/{id}/status` — удобнее через Postman или простой скрипт.

### 2.2 Мониторинг — что именно смотреть

Есть **3 уровня**, выбирай один в зависимости от зрелости:

**Уровень 0 — ничего не ставим (подходит первые 1–2 недели):**
- UptimeRobot (бесплатно, 50 мониторов): https://uptimerobot.com → добавь `https://mspshield.ru` и `https://mspshield.ru/api/health`. Алерт в Telegram.
- Health-check cron на своём ноуте: `curl -f https://mspshield.ru/api/health || notify-send` — раз в минуту.

Этого **достаточно для первого клиента**. Мониторинг клиента = отдельная история (см. `docs/deployment/tenant_onboarding.md`).

**Уровень 1 — docker-compose monitoring stack (когда > 2 клиентов):**
```bash
cd technical/0_Common/docker
cp .env.example .env            # заполнить GRAFANA_ADMIN_PASSWORD
docker compose --profile monitoring up -d
# Grafana: http://<IP-мониторинга>:3000
# Prometheus: http://<IP-мониторинга>:9090
```

**Уровень 2 — отдельная Monitoring VM через Ansible** — когда перейдёшь на Silver/Gold клиентов (см. `docs/deployment/tenant_onboarding.md`).

### 2.3 Еженедельный ритуал (10 минут каждый понедельник)

1. Открыть Telegram-чат с заявками — пересчитать, сколько новых.
2. `ssh ubuntu@10.10.0.2 && docker compose ps` — все ли сервисы Up.
3. `curl https://mspshield.ru/api/health` — отвечает ли API.
4. Посмотреть Let's Encrypt cert: `echo | openssl s_client -connect mspshield.ru:443 2>/dev/null | openssl x509 -noout -dates`. Если `notAfter` < 7 дней — certbot умер, см. траблшутинг.
5. Записать в `docs/checklists/weekly.md` (или Kaiten) — «прошёл checklist».

---

## 3. Изменение сайта

### 3.1 Как вообще «катить» изменения

Философия: **не редактируем код на сервере. Редактируем локально → push → перекатываем контейнер.**

Общий цикл:

```bash
# 1. На своём ноуте:
git checkout -b fix/pricing-silver
# ... редактируешь файлы ...
git add -p                         # ревью-режим, показывает каждый hunk
git commit -m "pricing: Silver 50k → 55k"
git push -u origin fix/pricing-silver
# Открываешь PR на GitHub → мёрджишь в main

# 2. На landing-VM:
ssh ubuntu@10.10.0.2
cd mspshield
git pull origin main
cd deploy
docker compose up -d --build      # пересоберёт frontend, backend, поднимет заново
```

**Всё изменение сайта — это локальный git commit + docker compose up на сервере.**

### 3.2 Изменить цифру (например, цену тарифа)

| Что хочу поменять | Файл | Строка |
|---|---|---|
| Цены тарифов (25 000 / 50 000 / 85 000 ₽) | `frontend/src/components/sections/Pricing.jsx` | массив `PLANS` |
| Годовая выручка клиента по умолчанию в ROI-калькуляторе | `frontend/src/components/sections/Pain.jsx` | `useState(3_000_000)` |
| SLA цифры (1/2/4 часа) | `frontend/src/components/sections/Pricing.jsx` + `frontend/src/components/sections/FAQ.jsx` | поиск по `1 час`, `2 часа`, `4 часа` |
| Цифры в Hero (если добавятся) | `frontend/src/components/sections/Hero.jsx` | |
| Email / телефон в футере | `frontend/src/components/Footer.jsx` | |
| Название ИП / ИНН в футере | `frontend/src/components/Footer.jsx` | |

Пример — сменить цену Silver:

```bash
grep -n "50 000" frontend/src/components/sections/Pricing.jsx
# Видим: price: "50 000 ₽/мес"
# Меняем на 55 000:
sed -i 's/50 000 ₽\/мес/55 000 ₽\/мес/' frontend/src/components/sections/Pricing.jsx
```

Или просто открыть файл в VS Code и поменять руками — абсолютно валидно.

### 3.3 Удалить блок / секцию

Пример — убрать секцию FAQ.

Шаг 1. **Удалить импорт и JSX из Landing.jsx:**

```jsx
// frontend/src/pages/Landing.jsx
// УБРАТЬ строку:
import FAQ from "@/components/sections/FAQ";
// И в JSX убрать:
<FAQ />
```

Шаг 2. **Удалить сам файл (опционально, чтобы не мусорить):**

```bash
git rm frontend/src/components/sections/FAQ.jsx
```

Шаг 3. **Проверить, что больше нигде не ссылаются:**

```bash
grep -r "FAQ" frontend/src/
# Если findings только в удалённых строках — чисто.
```

Шаг 4. **Пересобрать:**

```bash
cd frontend && yarn build    # локально — проверить, что билд не падает
```

Шаг 5. **Push + pull + compose up на сервере** (см. 3.1).

### 3.4 Заменить блок (удалить старый, вставить новый)

Тот же порядок что в 3.3, но шаг 1 — вместо удаления JSX, заменить на новый компонент:

```jsx
// Было:
<FAQ />
// Стало:
<Testimonials />                    // новый компонент, который ты создашь в components/sections/
```

И создать файл `frontend/src/components/sections/Testimonials.jsx` по образцу любого существующего (проще всего скопировать `FAQ.jsx` и переделать содержимое).

### 3.5 Изменить текст / заголовок

Большинство текстов находится **прямо в JSX-компонентах**, это не i18n-файлы. Поиск:

```bash
grep -rn "ваша инфраструктура работает" frontend/src/
```

Откроет строку → редактируем → коммит.

### 3.6 Когда нужно перезапустить только backend (не frontend)

Если поменял только `backend/*.py` или `backend/.env`:

```bash
docker compose up -d --no-deps --build backend
```

Frontend не трогает — пользователь не увидит «мигания».

### 3.7 Опасные зоны (перед изменением — сделать бэкап)

| Зона | Что там страшного | Как защититься |
|---|---|---|
| `backend/server.py` | Ломать API = сломать и форму, и Telegram-уведомления | Сначала тест локально `python -m pytest backend/tests/` |
| `deploy/nginx/mspshield.conf` | Ломать nginx = сайт недоступен | `sudo nginx -t` ДО reload |
| `backend/.env` | Потерять `TELEGRAM_BOT_TOKEN` → заявки не приходят | Бэкап в Vaultwarden |
| MongoDB | Удалить `db.leads.drop()` = потерять всех клиентов | `docs/deployment/disaster_recovery.md` |

---

## 4. Траблшутинг

> Принцип: **сначала смотри логи, потом гугли, потом меняй код.**

### 4.1 Сайт не открывается вообще

```bash
# 1. DNS живой?
dig +short mspshield.ru
# Ожидаем твой IP. Если пусто — регистратор сбросил или TTL протух.

# 2. VM жива?
ping <IP>
# Нет ответа — проверить в Yandex Cloud console, не выключена ли VM / не кончились ли деньги.

# 3. Nginx работает?
ssh ubuntu@<IP>
sudo systemctl status nginx
sudo nginx -t                          # синтаксис конфига
sudo tail -50 /var/log/nginx/error.log

# 4. Порт 443 открыт?
sudo ss -tlnp | grep ':443'
# Должна быть строка nginx. Если нет — security-group в YC заблокировал 443.
```

### 4.2 Сайт открывается, но белый экран / JS не грузится

```bash
# 1. Собрался ли фронт?
ssh ubuntu@<IP>
ls -la /var/www/mspshield/static/js/          # должны быть main.*.js файлы
docker compose logs frontend | tail -30       # ERROR при сборке?

# 2. Посмотреть в браузере DevTools → Console — там точная ошибка.
# Самая частая: REACT_APP_BACKEND_URL не задан → fetch падает с 404 на относительных путях.
cat frontend/.env
# Должно быть REACT_APP_BACKEND_URL=https://mspshield.ru
```

### 4.3 Форма «крутится» бесконечно / не отправляется

```bash
# 1. Backend отвечает?
curl -v https://mspshield.ru/api/health

# 2. CORS не блокирует?
# DevTools → Network → POST /api/leads → смотри статус.
# CORS-ошибка = backend вернул без нужных Access-Control-*.
# Фикс: backend/.env → CORS_ORIGINS=https://mspshield.ru

# 3. Rate-limit не сработал?
# Backend режет >10 req/мин с одного IP.
# В логах: "rate limit exceeded" — подожди минуту.
docker compose logs backend | tail -50
```

### 4.4 Заявки перестали приходить в Telegram

```bash
# В MongoDB они есть?
docker exec -it deploy-mongo-1 mongosh mspshield --eval 'db.leads.find().sort({created_at:-1}).limit(3)'

# Если ДА — проблема в Telegram-интеграции:
docker compose logs backend | grep -i telegram
# Частые причины:
#  - TELEGRAM_BOT_TOKEN протух (редко, но бывает если бот удалили)
#  - TELEGRAM_CHAT_ID в числовом формате, а в .env строкой
#  - Бот выгнан из чата

# Если заявок НЕТ ВООБЩЕ в Mongo — проблема в приёме на backend, см. 4.3.
```

### 4.5 SSL / сертификат истёк

```bash
# Проверить дату истечения:
echo | openssl s_client -connect mspshield.ru:443 2>/dev/null | openssl x509 -noout -dates

# Форс-обновить:
sudo certbot renew --force-renewal
sudo systemctl reload nginx

# Если certbot ругается «cannot obtain cert» — скорее всего DNS не резолвится
# с публичных резолверов, проверь dig @8.8.8.8 mspshield.ru
```

### 4.6 Mongo не стартует / «failed to connect»

```bash
docker compose logs mongo | tail -30

# Самое частое:
#  1. Нет места на диске: df -h → /var/lib/docker забит
#     Фикс: docker system prune -a --volumes  (ВНИМАНИЕ: снесёт все остановленные volumes!)
#  2. Повреждение WiredTiger после резкого reboot:
#     docker compose down
#     sudo chown -R 999:999 /var/lib/docker/volumes/deploy_mongo_data/_data
#     docker compose up -d mongo
```

### 4.7 Terraform: `terraform apply` упал

| Ошибка | Причина | Фикс |
|---|---|---|
| `Error 403: service accounts limit exceeded` | В фолдере кончились service-account slots | `yc iam service-account list` → удалить неиспользуемые |
| `Error 400: image not found` | Образ Ubuntu LTS сменил ID | `variables.tf`: обновить `image_id` через `yc compute image list --folder-id standard-images` |
| `Error 429: quota exceeded` | Превышена квота на vCPU / RAM в YC | Запросить увеличение в консоли YC |

### 4.8 Ansible: «role not found»

Известная проблема в v4.2 — `site.yml` ссылается на роли (`baseline`, `nginx`, `fastapi_backend`, `mongo`, `wireguard_hub`, `monitoring_agent`, `restic_client`, `base_hardening`, `ad_health_check`), которые ещё не имплементированы как директории `roles/*`.

**Текущий обход:** использовать Ansible только для **патчей уже работающей VM** (`playbooks/patch_nondisruptive.yml`) и `backup_install.yml`. Первичная раскатка делается вручную по `docs/deployment/landing_production.md`.

Роли будут добавлены в спринте 5 Этапа 4 (`docs/roadmap/etape_4_sprints.md`).

### 4.9 Что делать, когда «всё сломалось и я не понимаю что»

1. Скрин ошибки + `docker compose logs backend frontend mongo | tail -100` → открой issue в github.com/i1yxaluk-del/Newbie.
2. Если критично **прямо сейчас** — откат к предыдущему релизу:
   ```bash
   cd /home/ubuntu/mspshield
   git log --oneline -10              # найти хороший коммит
   git checkout <sha>
   cd deploy && docker compose up -d --build
   ```
3. Если и это не помогает — **DR из бэкапа** по `docs/deployment/disaster_recovery.md`.

---

## 5. Быстрая шпаргалка (распечатать и положить рядом с ноутом)

```
Обновить сайт:            git pull && docker compose up -d --build
Только backend:           docker compose up -d --no-deps --build backend
Посмотреть заявки:        docker exec -it deploy-mongo-1 mongosh mspshield --eval 'db.leads.find()'
Проверить здоровье:       curl https://mspshield.ru/api/health
Обновить сертификат:      sudo certbot renew --force-renewal && sudo systemctl reload nginx
Логи фронта:              docker compose logs frontend | tail -50
Логи бэка:                docker compose logs backend | tail -50
Перезапустить nginx:      sudo nginx -t && sudo systemctl reload nginx
Откатиться на прошлый:    git checkout <sha> && docker compose up -d --build
```

---

## 6. Связанные документы

- `docs/deployment/README.md` — оглавление всей деплой-доки.
- `docs/deployment/landing_production.md` — пошаговый production-деплой (9 шагов).
- `docs/deployment/local_dev.md` — как поднять локально для разработки.
- `docs/deployment/tenant_onboarding.md` — онбординг первого клиента.
- `docs/deployment/disaster_recovery.md` — сценарии потери данных.
- `docs/deployment/secrets_management.md` — где и как хранить ключи.
- `docs/deployment/troubleshooting.md` — более глубокие проблемы инфры.
- `docs/audit/v4.2_report.md` — отчёт аудита техинструкций v4.2.

---

## 7. История / что изменилось в v4.2

1. Лендинг **упрощён** до 9 секций (было 12): удалены Compare/Tools/Cases, сжаты Compliance/Process/FAQ/HowItWorks.
2. Убрано всё, что связано с платформой **Emergent** (badge, скрипты, `@emergentbase/visual-edits`, `emergentintegrations` в requirements) — теперь проект полностью независим.
3. Починены тесты backend (хардкод `/app/frontend/.env` → относительный путь).
4. Из `docker-compose.yml` убран устаревший атрибут `version:`.
5. Добавлен `technical/0_Common/docker/.env.example` — без него monitoring-compose не стартовал.
6. Создан этот документ.
