# Стек: назначение, зависимость и обучение

[← Книга](BOOK.md) · [Видеотека](VIDEO_GUIDE.md)

Не все инструменты одновременно нужны клиенту. Статус каждого контура указан в [текущей картине](CURRENT_STATE.md). Документация ниже углубляет механизм; версии команд сверяются с проектом.

| Инструмент | Для чего / от чего зависит | Углубление | Практический итог |
|---|---|---|---|
| Linux/systemd | Процессы, права, службы; ОС/пользователи/диск | [Debian handbook, RU](https://debian-handbook.info/browse/ru-RU/stable/), [systemd](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) | Процесс→порт→конфиг→данные→журнал |
| SSH/AmneziaWG/DNS/TLS | Доступ/маршрут/имя/защита; ключи, сеть, доверие | [Amnezia](https://docs.amnezia.org/), [MDN HTTP](https://developer.mozilla.org/ru/docs/Web/HTTP) | Различить сбой DNS, TCP, TLS, HTTP |
| Git/GitHub/Actions | История, review, автоматические проверки | [Pro Git RU](https://git-scm.com/book/ru/v2), [Actions](https://docs.github.com/ru/actions) | Учебный commit/revert, смысл CI |
| Docker/Compose | Приложения/сети/тома на VM | [Docker getting started](https://docs.docker.com/get-started/), [Compose](https://docs.docker.com/compose/) | Пересоздать test container без потери test data |
| Cloud.ru/Yandex Cloud | VM, сеть, IAM, хранение/счета | [Cloud.ru docs](https://cloud.ru/docs), [Yandex Cloud RU](https://yandex.cloud/ru/docs) | Ресурсы/права/стоимость/удаление стенда |
| Terraform/cloud-init | IaC/первичная подготовка альтернативной среды | [Terraform](https://developer.hashicorp.com/terraform/tutorials), [cloud-init](https://cloudinit.readthedocs.io/) | Объяснить state/первый boot, не смешивать live контуры |
| Python/FastAPI/Pydantic | API и проверка входа; окружение, БД, сеть | [Python tutorial](https://docs.python.org/3/tutorial/), [FastAPI RU](https://fastapi.tiangolo.com/ru/tutorial/), [Pydantic](https://docs.pydantic.dev/) | Проследить валидный/невалидный запрос |
| MongoDB/Motor | Документы и async доступ; сеть/индексы/credentials | [MongoDB manual](https://www.mongodb.com/docs/manual/), [Motor](https://motor.readthedocs.io/) | Сохранение/поиск/backup, не путать ID |
| React/CRA/CRACO | Браузерный интерфейс/сборка | [React RU](https://ru.react.dev/learn), [MDN JS](https://developer.mozilla.org/ru/docs/Web/JavaScript/Guide), [CRACO](https://craco.js.org/docs/) | Компонент→JSON→bundle→published page |
| Kaiten | Рабочие стадии/задачи/сроки, не secret store | [Kaiten help](https://faq.kaiten.ru/) | Карточка с источником, owner/next action/результатом |
| Метрика/Директ | Поведение/цели/привлечение; законные данные, budget | [Обучение Яндекса](https://yandex.ru/adv/edu), [Метрика](https://yandex.ru/support/metrica/) | Синтетическая воронка до оплаты, не CTR ради CTR |
| Prometheus/exporters | Метрики/правила; доступные targets | [Prometheus overview](https://prometheus.io/docs/introduction/overview/) | Target→ряд→правило |
| Grafana | Представление запросов, datasource UID | [Grafana fundamentals](https://grafana.com/tutorials/grafana-fundamentals/) | Реальный календарь и browser check |
| Alertmanager/MAX/Matrix alerter | Доставка/группировка; каналы, сессии/TLS | [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/), [MAX API](https://dev.max.ru/docs-api), [проект MAX](../docs/MAX_SETUP.md) | Тестовая доставка + подтверждение |
| Stalwart/Postbox | Почта/relay; DNS, ключи, репутация | [Stalwart docs](https://stalw.art/docs/), [Postbox RU](https://yandex.cloud/ru/docs/postbox/) | Источник→SMTP→получатель, выбранный маршрут |
| restic/S3 | Шифрованные копии; ключи/данные/консистентность | [restic](https://restic.readthedocs.io/en/stable/) | Прикладной restore в чистую среду |
| Vaultwarden | Управление секретами; учётки/MFA/recovery | [Wiki](https://github.com/dani-garcia/vaultwarden/wiki) | Персональные права/аварийный доступ |
| Synapse/MAS/Element | Сообщения/авторизация/клиент | [Synapse](https://element-hq.github.io/synapse/latest/), [MAS](https://element-hq.github.io/matrix-authentication-service/), [Matrix](https://spec.matrix.org/) | Отличить регистрацию, browser session и app login |
| LiveKit/Prosody/ntfy | Звонки/XMPP/push отдельными контурами | [LiveKit](https://docs.livekit.io/), [Prosody](https://prosody.im/doc/), [ntfy](https://docs.ntfy.sh/) | Цель, порты, права и отдельный backup |
| Wazuh | События/правила/поиск; агенты/feed/индексы | [Официальное руководство](https://documentation.wazuh.com/current/), [наш курс](../docs/training/wazuh/README.md) | Собственные и штатные правила с контрольными случаями |
| Ansible | Управление состоянием; inventory/SSH/модули | [Getting started](https://docs.ansible.com/ansible/latest/getting_started/index.html), [наш курс](../docs/training/ansible/README.md) | Два применения, возврат и объяснение границ |
| 1С/AD/БД/Kaspersky | Возможные клиентские системы, не автоматически установленный пакет | [1С](https://its.1c.ru/), [Microsoft Learn AD](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/), [Kaspersky support](https://support.kaspersky.ru/) | Источник/версия/лицензии/совместимость и scope до подключения |

## Правовые и финансовые источники

[ФНС НПД](https://npd.nalog.ru/), [ФНС НДС](https://www.nalog.gov.ru/rn77/taxation/taxes/nds/), [152-ФЗ](https://www.consultant.ru/document/cons_doc_LAW_61801/), [38-ФЗ](https://www.consultant.ru/document/cons_doc_LAW_58968/), [маркировка рекламы Яндекса](https://yandex.ru/adv/ad-labeling). Это первичные маршруты проверки, не персональная юридическая рекомендация. Дату применимости нормы проверяют на дату сделки.
