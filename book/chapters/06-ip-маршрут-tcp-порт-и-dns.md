# 6. IP, маршрут, TCP, порт и DNS

> **Учебная ситуация.** IP пингуется, но из РФ не открываются 22/80/443.

## Главное

IP отвечает на вопрос, к какому интерфейсу доставлять packet; route выбирает следующий hop. ICMP echo и TCP SYN — разные протоколы и могут фильтроваться по-разному.

Listening сетевое подключение связывает процесс с address:port. `127.0.0.1:8001` доступен только локально; `0.0.0.0:8001` принимает на всех интерфейсах.

DNS возвращает записи, но не проверяет TCP, TLS или application. TTL влияет на время распространения изменения и rollback.

## Как это работает

Диагностика идёт слоями: resolver возвращает IP; routing выбирает путь; SYN/SYN-ACK/ACK создаёт TCP; TLS проверяет имя и ключ; HTTP возвращает status; application выполняет бизнес-операцию. Перескакивание сразу к logs приложения тратит время, если SYN вообще не дошёл.

## Пример

```bash
dig +short example.org A
ip route get 1.1.1.1
ss -lntp
nc -vz -w3 203.0.113.10 443
curl -v --connect-timeout 5 https://example.org/health
```

## Практикум

1. Сделайте проверки с VM и из внешней сети.
2. Сопоставьте timeout, refused и HTTP 503.
3. Постройте дерево диагностики снизу вверх.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Timeout | packet/route/firewall, а не доказательство падения app. |
| Refused | host достижим, но сетевое подключение не слушает либо reject активен. |

## Источники проекта

- [docs/развёртываниеment/DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/DEPLOY_RUNBOOK.md)
- [docs/развёртываниеment/MIGRATION_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/развёртываниеment/MIGRATION_RUNBOOK.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

