# MSPShield Academy

Версия проекта: `89249e43a4e8b2e90d562307ef244ba95288c64c`. Формат: отдельные Markdown-главы.

Учебник рассчитан на Junior-сисадмина. Идите последовательно: знания вводятся до первого использования. Практикумы выполняйте на отдельной VM. Критерий завершения — самостоятельное действие и восстановление после ошибки, а не чтение текста.

## Как учиться

1. Прочитайте ситуацию и сначала запишите собственную гипотезу.
2. Разберите пример построчно; неизвестный токен найдите в официальной документации.
3. Выполните guided lab.
4. Закройте текст и выполните самостоятельную работу.
5. Через неделю повторите ключевую команду и объяснение из памяти.
6. Ведите `learning-log.md`: дата, задача, ошибка, механизм, исправление.
7. Все destructive-действия, firewall/DNS changes, `--drop`, restore поверх данных и production credentials сначала отрабатываются на lab; перед production нужен change с rollback.

## Научиться видеть систему

1. [От услуги к работающей системе](chapters/01-от-услуги-к-работающей-системе.md)
2. [Исследование незнакомой системы без угадывания](chapters/02-исследование-незнакомой-системы-без-угадывания.md)

## Linux и сеть

3. [Файлы, каталоги, пользователи и права](chapters/03-файлы-каталоги-пользователи-и-права.md)
4. [Процессы, signals, systemd и журналы](chapters/04-процессы-signals-systemd-и-журналы.md)
5. [Shell без магии](chapters/05-shell-без-магии.md)
6. [IP, маршрут, TCP, порт и DNS](chapters/06-ip-маршрут-tcp-порт-и-dns.md)
7. [HTTP, TLS и reverse proxy](chapters/07-http-tls-и-reverse-proxy.md)

## Код и конфигурация

8. [Git как история решений](chapters/08-git-как-история-решений.md)
9. [YAML и .env как разные языки](chapters/09-yaml-и-env-как-разные-языки.md)
10. [Python-путь запроса: от socket до функции](chapters/10-python-путь-запроса-от-socket-до-функции.md)
11. [MongoDB, persistence и consistency](chapters/11-mongodb-persistence-и-consistency.md)
12. [Интеграции и durable outbox](chapters/12-интеграции-и-durable-outbox.md)
13. [Frontend и форма как недоверенный клиент](chapters/13-frontend-и-форма-как-недоверенный-клиент.md)

## Контейнеры и deploy

14. [Что Docker изолирует, а что нет](chapters/14-что-docker-изолирует-а-что-нет.md)
15. [Dockerfile, cache и attack surface](chapters/15-dockerfile-cache-и-attack-surface.md)
16. [Compose как граф зависимостей](chapters/16-compose-как-граф-зависимостей.md)
17. [Облако и VM с нуля](chapters/17-облако-и-vm-с-нуля.md)
18. [Полный deploy MSPShield](chapters/18-полный-deploy-mspshield.md)

## Production и эксплуатация

19. [SMTP, DNS и Stalwart/Postbox](chapters/19-smtp-dns-и-stalwart-postbox.md)
20. [Метрики и Prometheus](chapters/20-метрики-и-prometheus.md)
21. [Alerting и доставка в MAX](chapters/21-alerting-и-доставка-в-max.md)
22. [Backup, restore, RPO и RTO](chapters/22-backup-restore-rpo-и-rto.md)
23. [Миграция и Disaster Recovery](chapters/23-миграция-и-disaster-recovery.md)
24. [Secrets, Vaultwarden и доступ](chapters/24-secrets-vaultwarden-и-доступ.md)
25. [Харденинг и безопасные изменения](chapters/25-харденинг-и-безопасные-изменения.md)
26. [Incident, problem, change и service review](chapters/26-incident-problem-change-и-service-review.md)
27. [Технический capstone: построить аналог с нуля](chapters/27-технический-capstone-построить-аналог-с-нуля.md)

## Экономика MSP

28. [Деньги и время: язык модели](chapters/28-деньги-и-время-язык-модели.md)
29. [Capacity и путь от подработки к команде](chapters/29-capacity-и-путь-от-подработки-к-команде.md)
30. [Из технического scope в пакет и цену](chapters/30-из-технического-scope-в-пакет-и-цену.md)

## Продажи и lifecycle

31. [ICP и ценностное предложение без тумана](chapters/31-icp-и-ценностное-предложение-без-тумана.md)
32. [Воронка как управляемый процесс](chapters/32-воронка-как-управляемый-процесс.md)
33. [Discovery и безопасный pre-audit](chapters/33-discovery-и-безопасный-pre-audit.md)
34. [КП, переговоры и скидки](chapters/34-кп-переговоры-и-скидки.md)
35. [Договор, SLA, Периметр и ПДн](chapters/35-договор-sla-периметр-и-пдн.md)
36. [Onboarding, steady state и offboarding](chapters/36-onboarding-steady-state-и-offboarding.md)
37. [Owner dashboard и управленческие решения](chapters/37-owner-dashboard-и-управленческие-решения.md)
38. [Финальный бизнес-capstone](chapters/38-финальный-бизнес-capstone.md)

## Практические руководства по стеку

- [GitHub для Owner: ветки, PR, review, CI и откат](guides/GITHUB_OWNER_WORKFLOW.md)
- [Yandex Cloud: IAM, сеть, VM, deploy и расходы](guides/YANDEX_CLOUD_OWNER.md)
- [Kaiten для двухчленной MSP-команды](guides/KAITEN_OPERATIONS.md)
- [Стек продаж: qualification, discovery, pricing и handoff](guides/SALES_STACK.md)
- [Кураторская видеотека: конкретные материалы и практикумы](VIDEO_GUIDE.md)

## Приложения

- [Стандарт написания и контроль фактов](00_AUTHORING_STANDARD.md)
- [Исходная карта программы](00_BOOK_MAP.md)
- [Глоссарий](GLOSSARY.md)
- [Ответы и подсказки преподавателю](INSTRUCTOR_NOTES.md)
