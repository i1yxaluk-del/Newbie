# MSPShield / «МСП Облако»

Управляемый IT-сервис для малого и среднего бизнеса в РФ: автоматический мониторинг, резервное копирование, защищённый доступ и реакция в согласованное рабочее окно.

> Важно: «мониторинг 24/7» означает круглосуточную работу автоматики. Он не означает круглосуточное дежурство инженера. Gold и гарантированное 24/7-реагирование не продаются до выполнения операционного gate.

## Навигация

| Задача | Канонический документ |
|---|---|
| Цена, лимиты и маржа | [`docs/PRICING_SOURCE_OF_TRUTH.md`](docs/PRICING_SOURCE_OF_TRUTH.md) |
| Готовность 8/10 | [`docs/PROJECT_8_OF_10.md`](docs/PROJECT_8_OF_10.md) |
| Тарифная архитектура | [`technical/README.md`](technical/README.md) |
| Договорный комплект | [`contracts/README.md`](contracts/README.md) |
| Обучение Junior | [`docs/training/README.md`](docs/training/README.md) |
| Эксплуатационные runbook | [`docs/runbooks/README.md`](docs/runbooks/README.md) |
| Развёртывание | [`docs/deployment/README.md`](docs/deployment/README.md) |

## Коммерческие пакеты

| Пакет | Статус | Цена | Включённое ручное время | Реакция P1 |
|---|---|---:|---:|---|
| Bronze Pilot | продаётся | от 25 000 ₽/мес | 2 инженерных часа + 1 час service management | до 4 рабочих часов в согласованное окно |
| Silver Managed | после успешного Bronze | от 50 000 ₽/мес | 4 инженерных часа + 1,5 часа service management | до 2 рабочих часов в согласованное окно |
| Gold Future | закрыт до gate | от 120 000 ₽/мес | только индивидуальный расчёт | 24/7 только при дежурной ротации |

Сверхлимитные работы: от 3 500 ₽/ч. Срочные работы вне окна: коэффициент 2×, минимум 2 часа. Лицензии, дополнительное хранилище, миграции и устранение старого технического долга оплачиваются отдельно.

## Локальный запуск

```bash
git clone https://github.com/i1yxaluk-del/Newbie.git
cd Newbie
cp backend/.env.example backend/.env
docker compose -f deploy/docker-compose.yml up -d mongo
cd backend && pip install -r requirements.txt && uvicorn server:app --reload --port 8001
```

Для production используется `secure_server:app`, а не `server:app`. Production backend публикуется только через reverse proxy; порт `8001` не должен быть доступен из интернета.

## Правила безопасной работы

- Не коммитить `.env`, токены, ключи, пароли и backup credentials.
- Изменения production выполнять только по change record с rollback-планом.
- Junior не меняет production без подтверждения owner/senior, пока не пройдена матрица допуска.
- Юридические шаблоны нельзя отправлять клиенту без заполнения приложений и финальной проверки юристом.
