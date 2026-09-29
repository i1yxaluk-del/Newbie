# MSPShield Academy — оглавление и карта развития Owner

Базовая ревизия проекта: `89249e43a4e8b2e90d562307ef244ba95288c64c` (28.09.2026).

Это не готовая книга, а согласуемая архитектура. Главы будут писаться строго по порядку: каждая использует понятия предыдущих и добавляет один новый слой сложности. Итоговый `BOOK.md` будет навигационным файлом со ссылками на главы, а не копией текста.

## Как читать карту

- **Опора** — что читатель уже обязан понимать.
- **Разбираем** — конкретное содержание, а не список терминов.
- **Практика** — работа, которую действительно нужно выполнить.
- **На выходе** — материальный результат, подтверждающий навык.

# Часть I. Научиться видеть систему

## 1. От услуги к работающей системе

**Опора:** базовый опыт с Linux и представление о сайте.

**Разбираем:** зачем MSP-проекту одновременно нужны код, инфраструктура, эксплуатация, договор и экономика; путь заявки с landing в backend и Kaiten; путь alert из exporter через Prometheus и Alertmanager в MAX/email; где заканчивается факт и начинается обещание клиенту. Вводятся `component`, `interface`, `state`, `source of truth` и `failure domain` на одной схеме проекта.

**Практика:** нарисовать текущий MSPShield в draw.io/Mermaid и для каждой стрелки указать протокол или тип передачи.

**На выходе:** `architecture-context.md` — схема, список компонентов и пять вопросов, которые пока нельзя объяснить.

## 2. Как исследовать незнакомую систему без угадывания

**Опора:** глава 1.

**Разбираем:** чтение README и index-файлов; отличие исполняемого файла от инструкции и исторического отчёта; `--help`, man pages, logs, source code, version pin; как проверять утверждение двумя независимыми наблюдениями; статусы REPO FACT / EXTERNAL FACT / MODEL / ASSUMPTION.

**Практика:** восстановить назначение одного сервиса только по Compose, Dockerfile, README и healthcheck, затем сверить с фактическим запуском.

**На выходе:** короткий investigation report со ссылками на строки источников и перечнем неопределённостей.

# Часть II. Linux и сеть — фундамент, без которого Docker остаётся магией

## 3. Файлы, каталоги, пользователи и права

**Опора:** вход по SSH.

**Разбираем:** абсолютные и относительные пути; inode как модель, владелец/группа/mode; `rwx` для файла и каталога; umask; почему `.env` должен быть `600`; root-only каталог; как shell раскрывает glob до `sudo` и почему `sudo cp root-only/*.tar.gz` может не найти файлы.

**Практика:** создать дерево backup-артефактов, воспроизвести ошибку с glob, исправить через `sudo sh -c`, проверить владельца и режим.

**На выходе:** lab-log с командами, фактическими правами и объяснением каждой цифры в `chmod 640`.

## 4. Процессы, signals, systemd и журналы

**Опора:** глава 3.

**Разбираем:** process, PID/PPID, foreground/background; exit code; stdout/stderr; signals; daemon; unit, dependency и restart policy; почему `systemctl restart caddy` отличается от container restart; чтение `journalctl` по времени и unit.

**Практика:** написать простой systemd service для учебного HTTP-процесса, сломать ExecStart, найти причину в журнале и восстановить.

**На выходе:** рабочий unit-файл и troubleshooting note.

## 5. Shell без магии

**Опора:** главы 3–4.

**Разбираем:** tokenization; одинарные и двойные кавычки; переменные; command substitution; pipes; redirection; `&&` и `||`; `set -euo pipefail`; почему пароль в командной строке попадает в history/process list; как читать shell-скрипт сверху вниз.

**Практика:** построчно разобрать безопасную учебную версию `preflight.sh`, добавить проверку обязательной переменной и понятное сообщение об ошибке.

**На выходе:** аннотированный shell-скрипт без скрытых side effects.

## 6. IP, маршрут, TCP, порт и DNS

**Опора:** процессы и sockets.

**Разбираем:** IP-адрес интерфейса; routing table; NAT; TCP handshake; listening socket; разница `127.0.0.1`, `0.0.0.0` и container network; recursive DNS, A/MX/CNAME/TXT; TTL; почему ping не подтверждает TCP-доступность. Отдельно — production-урок о недоступном из РФ IP при работающем ICMP.

**Практика:** пройти путь `curl` от DNS до process, закрыть порт firewall, отличить timeout от connection refused и HTTP 503.

**На выходе:** диагностическое дерево «DNS / route / TCP / TLS / HTTP / application».

## 7. HTTP, TLS и reverse proxy

**Опора:** глава 6.

**Разбираем:** request/response; method, path, headers, status; сертификат, private key, chain, SNI; TLS termination; Caddy как reverse proxy; upstream; почему cloud-init заглушка отдаёт 503; почему systemd не видит Compose `.env`; роль `MSP_DOMAIN`.

**Практика:** поднять Caddy перед локальным backend, получить сертификат в тестовой среде либо использовать локальный CA, затем намеренно указать неверный upstream.

**На выходе:** рабочий Caddyfile, схема handshake и таблица симптомов 502/503/TLS error.

# Часть III. Код и конфигурация проекта

## 8. Git как история решений

**Опора:** работа с файлами.

**Разбираем:** working tree, index, commit graph, branch, remote; diff как основной объект review; merge/rebase без культовых правил; revert; PR и CI; pin версии; как commit `maxapi-python 2.1.2 → 2.4.1` связывается с production symptom.

**Практика:** создать ветку, внести одну осмысленную правку, разделить смешанный diff через `git add -p`, открыть локальный review и выполнить revert.

**На выходе:** линейная история из небольших объяснимых commits.

## 9. YAML и `.env` как два разных языка конфигурации

**Опора:** shell variables.

**Разбираем:** scalar, mapping, sequence; типы и кавычки; indentation; Compose interpolation; `${VAR:?error}`; YAML parse против schema validation; `.env` без BOM/CRLF; итог `docker compose config`; почему секрет после interpolation может попасть в вывод.

**Практика:** от минимального YAML перейти к Compose service; воспроизвести четыре ошибки — tab, неверный уровень, пустая env, неожиданный boolean.

**На выходе:** собственная памятка чтения YAML с реальными ошибками parser/schema/runtime.

## 10. Python-путь запроса: от socket до функции

**Опора:** HTTP и процессы.

**Разбираем:** interpreter, module/import, virtual environment, package pin; ASGI, Uvicorn и FastAPI; route decorator; request validation; sync/async на практическом уровне; exception и stack trace; health endpoint не как «сервер жив», а как определённая проверка.

**Практика:** написать маленький FastAPI-сервис с `/health` и `/requests`, типизированным body и корректными 400/422/500 сценариями.

**На выходе:** сервис с тестами и пояснением полного request lifecycle.

## 11. Данные: MongoDB, persistence и границы consistency

**Опора:** Python API.

**Разбираем:** document/collection; `_id`; query/update; индекс; connection string; container lifecycle против data lifecycle; atomic operation; race; idempotency key; почему Mongo dump не заменяет backup всех volumes.

**Практика:** создать заявку дважды с одним idempotency key и доказать, что бизнес-результат один; сделать dump и restore в отдельную database.

**На выходе:** модель данных заявки и reproducible restore.

## 12. Интеграции и durable outbox

**Опора:** главы 10–11.

**Разбираем:** почему нельзя одновременно записать Mongo и внешнюю систему одной обычной транзакцией; outbox record, worker, retry, backoff, dead letter; at-least-once и duplicate handling; чем «доставлено» отличается от «поставлено в очередь».

**Практика:** временно отключить fake CRM, накопить outbox, вернуть сервис и проверить доставку без двойных карточек.

**На выходе:** минимальная outbox-реализация и таблица гарантий.

## 13. Frontend и форма как недоверенный клиент

**Опора:** HTTP API.

**Разбираем:** browser runtime, DOM, SPA/component/state; build-time и runtime configuration; клиентская validation не является security control; consent; CAPTCHA fail-closed; CORS; что допустимо помещать в frontend bundle.

**Практика:** собрать landing, найти итоговые assets, отправить запрос в обход UI и убедиться, что backend повторно проверяет обязательные поля.

**На выходе:** схема validation layers и проверенная production-сборка.

# Часть IV. Контейнеры и воспроизводимое развёртывание

## 14. Что Docker изолирует, а что нет

**Опора:** Linux processes, files и network.

**Разбираем:** image layers, container process, namespaces, cgroups, writable layer; bind mount и named volume; user внутри container; bridge и embedded DNS; ports syntax. Детально разбирается `127.0.0.1:8001:8001` и причина не публиковать Mongo/9095.

**Практика:** собрать image, запустить container, потерять данные в writable layer, затем сохранить их в volume и исследовать network namespace.

**На выходе:** таблица «image/container/volume/bind mount» с наблюдаемым экспериментом.

## 15. Dockerfile: воспроизводимость, cache и attack surface

**Опора:** глава 14.

**Разбираем:** build context, `FROM`, `COPY`, `RUN`, `WORKDIR`, `USER`, `CMD/ENTRYPOINT`; cache invalidation; pin dependencies; multi-stage; секреты во время build; минимальный runtime image.

**Практика:** написать Dockerfile для учебного FastAPI и улучшить его по размеру, непривилегированному пользователю и cache.

**На выходе:** два image и измеримое сравнение.

## 16. Compose: приложение как граф зависимостей

**Опора:** YAML и Docker.

**Разбираем:** project/service/network/volume/profile; `depends_on` не означает готовность приложения; healthcheck; restart; env_file; resource limits; итоговая конфигурация; application и monitoring stacks MSPShield.

**Практика:** собрать Mongo + backend + proxy; затем добавить healthcheck и доказать, какие сбои restart policy не исправляет.

**На выходе:** Compose-проект, который переживает recreate без потери данных.

## 17. Облако и VM с нуля

**Опора:** Linux, network, Docker.

**Разбираем:** account, service account, IAM key, network/subnet/security group, static public IP, disk; cloud-init; preemptible VM; bootstrap dependency; ForceIPv4, unzip и Node lessons; разделение cloud firewall и ufw.

**Практика:** создать учебную VM по Infrastructure checklist, дождаться cloud-init, проверить base-ready и удалить ресурсы без orphan cost.

**На выходе:** журнал создания VM с resource inventory и cost estimate.

## 18. Полный deploy MSPShield

**Опора:** части II–IV.

**Разбираем:** порядок repo → secrets → preflight → application stack → monitoring → Caddy → DNS; почему порядок важен; три env-файла; webroot; health checks; gates до переключения трафика.

**Практика:** чистое развёртывание по `DEPLOY_RUNBOOK.md` без копирования неизвестных команд; после каждого шага объяснить изменённое состояние.

**На выходе:** deployment record, redacted config inventory и go/no-go решение.

# Часть V. Сервисы production и эксплуатация

## 19. Почта: SMTP, DNS и Stalwart/Postbox

**Опора:** DNS/TLS и credentials.

**Разбираем:** envelope vs headers; SMTP submission/relay/delivery; MX, SPF, DKIM, DMARC; local domain; Stalwart route; Postbox implicit TLS 465; DKIM CNAME; JMAP admin; очередь и 535; почему изменение `.env` не меняет восстановленный route в Stalwart DB.

**Практика:** настроить тестовый outbound route, посмотреть queue через JMAP, воспроизвести неверный credential и восстановить доставку с restart.

**На выходе:** mail-flow diagram и диагностическая карта identity/DNS/auth/queue.

## 20. Метрики и Prometheus

**Опора:** HTTP и services.

**Разбираем:** counter/gauge/histogram; labels и cardinality; scrape/target/time series; node-exporter, cAdvisor, blackbox; PromQL от selector до rate; почему dashboard не является SLA.

**Практика:** написать три запроса и одну recording rule, затем создать плохой high-cardinality label и оценить последствия.

**На выходе:** dashboard с объяснением источника каждого графика.

## 21. Alerting и доставка в MAX

**Опора:** Prometheus и HTTP webhook.

**Разбираем:** alert rule, `for`, labels/annotations; Alertmanager grouping/routing/inhibition; bearer token; MAX userbot, `maxapi-python 2.4.1`, SMS+2FA, `/session/max.db`, bind mount, fallback. Отдельно — различие health сервиса и фактической доставки сообщения.

**Практика:** провести P1 от искусственной метрики до MAX, затем сломать session и проверить fallback/failed log; после reboot доказать сохранность session.

**На выходе:** timestamped alert-delivery evidence и recovery note.

## 22. Backup, restore, RPO и RTO

**Опора:** volumes и data models.

**Разбираем:** backup set; consistency; dump vs filesystem copy; encryption; restic snapshot/repository/check/retention; 3-2-1 как принцип, не сертификат; фактические RPO/RTO. Разбираются Mongo, Vaultwarden, оба Stalwart volume и MAX session.

**Практика:** создать backup, удалить учебное состояние, восстановить в clean environment и измерить потерю данных/время.

**На выходе:** restore report с измеренными RPO/RTO и расхождениями.

## 23. Миграция и Disaster Recovery

**Опора:** deploy и restore.

**Разбираем:** migration vs DR; inventory, freeze/capture, artifact transfer, clean VM, verification, cutover, observation, rollback; плоская/вложенная раскладка; empty-volume fail; Stalwart bootstrap; региональный TCP gate; DNS TTL.

**Практика:** полный перенос на новую VM без переключения production DNS, затем controlled cutover учебного домена и rollback rehearsal.

**На выходе:** migration pack и подписанный go/no-go checklist.

## 24. Secrets, Vaultwarden и доступ

**Опора:** Linux permissions и identity.

**Разбираем:** secret lifecycle; generation, storage, delivery, use, rotation, revocation; MFA; least privilege; break-glass; access matrix; почему `docker compose config` может раскрыть значения; границы ПДн и секретов в Kaiten/Git.

**Практика:** создать Vaultwarden collection для учебного клиента, выдать и отозвать доступ, выполнить rotation без записи секрета в ticket.

**На выходе:** access matrix и redacted rotation evidence.

## 25. Харденинг и безопасные изменения

**Опора:** cloud networking, secrets, backup.

**Разбираем:** attack surface; patching; SSH keys; AWG; закрытие публичного 22 на SG и ufw только после tunnel test; аварийный возврат; change plan, maintenance window и rollback.

**Практика:** на учебной VM ограничить SSH VPN-подсетью, проверить отказ снаружи и доступ через tunnel, затем воспроизвести break-glass.

**На выходе:** hardening record без потери управляемости.

## 26. Incident, problem, change и service review

**Опора:** monitoring, runbooks и архитектура.

**Разбираем:** incident vs problem; severity; triage; mitigation vs root cause; timeline; communication; postmortem без обвинений; change failure rate; monthly service review. Используются сценарии Caddy 503, MAX unsupported version, Postbox 535 и недоступный IP.

**Практика:** tabletop P1 с ролями Owner/Product Manager/Junior, затем техническое восстановление и postmortem.

**На выходе:** incident pack, problem record и одна проверяемая preventive action.

## 27. Технический capstone — построить аналог с нуля

**Опора:** главы 1–26.

**Разбираем:** не новые термины, а перенос знаний. Требование: спроектировать и развернуть уменьшенный аналог без копирования Compose целиком; обосновать компоненты, данные, alerts, backup и security boundaries.

**Практика:** пустая VM → приложение → TLS → monitoring → alert → backup → clean restore → runbook → handover Junior.

**На выходе:** работающий стенд и защита архитектуры. Без успешного restore capstone не принят.

# Часть VI. Экономика MSP

## 28. Деньги и время: язык модели

**Опора:** технический capstone, чтобы стоимость была привязана к реальной работе.

**Разбираем:** revenue, cash receipt, variable/fixed cost, direct labor, contribution, profit; стоимость часа Owner; productive capacity; incident reserve; налоги и банк как параметры, а не константы.

**Практика:** собрать месячный P&L и cash-flow для одного Bronze, явно указав assumptions и sensitivity ±20% по часам.

**На выходе:** spreadsheet/model с формулами и проверкой единиц.

## 29. Capacity и путь от подработки к команде

**Опора:** глава 28.

**Разбираем:** календарные и productive hours; billable/non-billable; WIP; context switching; bus factor; обучение супруги/Product Manager и Junior; capacity gate для Gold; момент найма через workload и margin, а не желание.

**Практика:** построить три сценария — 2, 5 и 10 клиентов — с incident reserve, sales/admin и обучением.

**На выходе:** capacity plan и правила accept/waitlist/hire.

## 30. Из технического scope в пакет и цену

**Опора:** chapters 16, 28–29.

**Разбираем:** service catalog; included/excluded; onboarding fee; overage; pass-through; margin floor; risk premium; Bronze/Silver/Gold On Demand; почему низкая цена создаёт операционный долг.

**Практика:** оценить один реальный клиентский периметр, выбрать пакет, рассчитать floor price и сформировать Order Form без скрытых обязательств.

**На выходе:** pricing worksheet и решение о допустимой скидке.

# Часть VII. Продажи и клиентский lifecycle

## 31. ICP и ценностное предложение без маркетингового тумана

**Опора:** понимание услуги и её стоимости.

**Разбираем:** segment, ICP, anti-ICP, trigger, pain, impact, alternative, buyer/user; наблюдаемые признаки fit; различие функции и результата; проверяемое обещание.

**Практика:** провести пять problem interviews или разобрать пять компаний по открытым данным без продажи и без выдумывания боли.

**На выходе:** ICP card, anti-fit rules и три версии value proposition.

## 32. Воронка как управляемый процесс

**Опора:** глава 31.

**Разбираем:** New → Qualified → Discovery → Proposal → Capacity Check → Contract → Won/Lost/Waitlist; entry/exit criteria; next action; stage aging; conversion; win rate; sales cycle и sales velocity; почему перенос карточки не равен прогрессу.

**Практика:** настроить учебную Kaiten-доску и провести три фиктивные сделки, включая no-fit и Gold waitlist.

**На выходе:** stage policy и dashboard без vanity metrics.

## 33. Discovery и безопасный pre-audit

**Опора:** funnel и technical scope.

**Разбираем:** current state, desired state, impact, authority, timing, budget, constraints; письменное разрешение; граница между вопросами и активным сканированием; evidence и unknowns.

**Практика:** провести discovery по сценарию клиента и составить технический perimeter, assumptions и вопросы, не обещая решение до диагностики.

**На выходе:** discovery notes и qualification decision.

## 34. КП, переговоры и скидки

**Опора:** pricing и discovery.

**Разбираем:** proposal как ответ на подтверждённую проблему; options; anchoring без манипуляции; objection vs condition; BATNA; concession только в обмен на scope/term/prepayment; срок действия и capacity reservation.

**Практика:** подготовить Bronze/Silver options, ответить на «дорого» и пересчитать скидку 5% через margin, а не только revenue.

**На выходе:** коммерческое предложение и журнал решений.

## 35. Договор, SLA, Периметр и ПДн

**Опора:** технический scope и коммерческая модель.

**Разбираем:** MSA и Order Form; service description; reaction time vs resolution; exclusions/dependencies; liability cap; acceptance; change; termination/offboarding; DPA и юридическая проверка в РФ. Monitoring data не превращается автоматически в договорное SLA.

**Практика:** заполнить единый договор для учебного клиента и найти пять мест, где техническая реальность может противоречить обещанию.

**На выходе:** договорный пакет с legal-open-items, а не самодельное юридическое заключение.

## 36. Onboarding, steady state и offboarding

**Опора:** договор и operations.

**Разбираем:** payment/scope gate; access; inventory; baseline; monitoring; backup; acceptance; service review; renewal; data return/deletion; revocation. Kaiten хранит задачи и решения, Vaultwarden — secrets, Git — шаблоны, Prometheus — telemetry.

**Практика:** провести клиента через lifecycle на тестовом стенде и затем полностью отозвать доступ.

**На выходе:** client file без credentials в Git/Kaiten и offboarding evidence.

## 37. Owner dashboard и управленческие решения

**Опора:** unit economics и funnel.

**Разбираем:** MRR/ARR, contribution MRR, logo/MRR churn, NRR, CAC, payback, осторожный LTV, pipeline coverage, utilization, change failure rate и restore success. Для каждой метрики — формула, источник, когорта, период, порог и действие.

**Практика:** построить dashboard на синтетических данных и для каждого отклонения принять одно решение; затем проверить, не противоречат ли метрики друг другу.

**На выходе:** monthly owner review.

## 38. Финальный бизнес-capstone

**Опора:** главы 28–37.

**Разбираем:** перенос знаний на нового клиента.

**Практика:** квалифицировать компанию, провести discovery, определить perimeter, выбрать/изменить пакет, рассчитать capacity и margin, подготовить proposal/Order Form, спланировать onboarding и первые 90 дней. Отдельно решить, можно ли принять Gold и какие дополнительные силы нужны.

**На выходе:** полный decision pack и устная защита: почему клиента принимаем, ставим в waitlist или отказываем.

# Порядок написания глав

Главы создаются пакетами, чтобы не потерять связность:

1. `01–07` — фундамент и единая терминология.
2. `08–13` — код, данные и frontend.
3. `14–18` — контейнеры и deploy.
4. `19–27` — production services, operations и technical capstone.
5. `28–30` — экономика и capacity.
6. `31–38` — продажи, договор и business capstone.
7. Только затем создаётся `BOOK.md`, глоссарий вводимых терминов и cross-reference index.

После каждого пакета проверяются: отсутствие необъяснённых терминов; ссылки на предыдущие знания; отсутствие расхождений с main; реальная выполнимость практикумов; переход от worked example к самостоятельной работе.
