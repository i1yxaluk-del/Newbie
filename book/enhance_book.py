from pathlib import Path
import re
R=Path('/data/MSPShield_Academy_MD'); C=R/'chapters'
# Точные определения: термин раскрывается через механизм, границу и пример.
defs={
'interface':'Согласованная граница обмена между компонентами: адрес/протокол, формат, допустимые ошибки и ожидания по времени. `backend:8001` — сетевой интерфейс; Order Form — организационный интерфейс между продажей и эксплуатацией.',
'state':'Данные, от которых зависит следующий результат и которые переживают отдельную операцию: документ Mongo, файл session, volume, DNS-запись. Лог процесса не всегда является состоянием.',
'failure domain':'Набор компонентов, способных отказать вместе из-за общей зависимости. Все containers на одной VM имеют общий failure domain питания, диска и host kernel.',
'evidence':'Минимальный проверяемый артефакт: timestamp, exit code, hash, запрос/ответ, metric или подписанный документ. Скриншот зелёной панели без target и времени — слабое evidence.',
'inode':'Объект Linux filesystem с metadata и ссылками на blocks; имя находится в каталоге. Поэтому rename в пределах filesystem меняет directory entry, а не переписывает содержимое.',
'permission':'Проверяемое ядром право чтения, записи или выполнения для effective UID/GID процесса. `sudo` меняет identity команды, но не уже выполненное shell expansion.',
'process':'Запущенный экземпляр программы: address space, PID, credentials, environment и file descriptors. Service может породить несколько процессов.',
'signal':'Асинхронное уведомление процессу. SIGTERM допускает обработчик и graceful shutdown; SIGKILL выполняется ядром и не даёт очистить состояние.',
'unit':'Декларация systemd о том, как создать и контролировать ресурс. Active unit не доказывает, что внешний пользователь получает корректный ответ.',
'expansion':'Преобразование shell до запуска программы: `$VAR`, `$(command)`, glob `*`, quotes. Ошибка expansion означает, что вызываемая программа могла вообще не увидеть ожидаемый аргумент.',
'pipeline':'Соединение stdout одной команды со stdin следующей. Без `pipefail` status pipeline обычно равен status последней команды.',
'socket':'Kernel-объект endpoint. Listening TCP socket определяется address, port и protocol; firewall может блокировать путь, даже когда socket слушает.',
'route':'Правило выбора interface/next hop для destination. DNS может вернуть правильный IP, но route или провайдерская фильтрация всё равно сделают TCP недоступным.',
'DNS':'Распределённое сопоставление имён с typed records. Resolver cache уважает TTL; изменение authoritative записи не мгновенно меняет все ответы.',
'TLS':'Протокол шифрования и проверки identity endpoint. Certificate связывает public key с именами; private key нельзя публиковать.',
'reverse proxy':'Сервис, который завершает клиентское соединение и создаёт новое к upstream. Поэтому client↔Caddy и Caddy↔backend диагностируются отдельно.',
'commit':'Неизменяемый Git-объект со снимком дерева, metadata и parent links. Branch лишь указывает на один commit.',
'index':'Подготовленное содержимое следующего commit. Оно может отличаться и от working tree, и от HEAD.',
'schema':'Набор допустимых ключей, типов и ограничений поверх синтаксически корректных данных. YAML parser не знает правил Docker Compose.',
'interpolation':'Подстановка значения переменной инструментом до дальнейшей обработки. Compose interpolation происходит при построении модели, не внутри YAML стандарта.',
'ASGI':'Контракт вызовов между Python web server и asynchronous application. Uvicorn владеет socket, FastAPI обрабатывает scope/events.',
'middleware':'Обёртка вокруг application, которая может проверить или изменить запрос/ответ. Ошибка в чтении body способна лишить downstream исходных данных.',
'document':'BSON-объект MongoDB с полями и `_id`. Свободная структура не отменяет необходимость прикладной валидации и indexes.',
'index-db':'Структура, ускоряющая поиск и способная обеспечивать uniqueness. Она увеличивает стоимость записи и занимает storage.',
'idempotency':'Повтор операции с тем же ключом не создаёт второй бизнес-результат. Это не означает, что сетевой запрос физически выполняется один раз.',
'outbox':'Сохранённая рядом с бизнес-данными запись о требуемой внешней доставке. Worker удаляет её только после подтверждения каждого канала.',
'at-least-once':'Гарантия повторной попытки до подтверждения, допускающая дубли. Получатель должен иметь idempotency key или deduplication.',
'SPA':'Приложение, где browser загружает bundle и меняет UI без полной перезагрузки страницы. Код работает в недоверенной среде пользователя.',
'fail-closed':'При невозможности проверить разрешение операция отклоняется. Повышает безопасность, но требует продуманного UX и fallback для legitimate users.',
'image':'Неизменяемый шаблон root filesystem и metadata для container. Image не содержит runtime volume data.',
'namespace':'Механизм Linux, дающий процессу отдельное представление PID, mount, network и других ресурсов; ядро остаётся общим.',
'cgroup':'Механизм учёта и ограничения CPU, memory и других ресурсов группы процессов.',
'volume':'Storage с lifecycle отдельно от container. Backup volume всё равно должен учитывать consistency приложения.',
'build context':'Набор файлов, отправляемый builder. `.dockerignore` уменьшает размер и риск случайно включить secrets.',
'layer':'Неизменяемый результат инструкции image build. Удаление секрета следующим RUN не гарантирует его исчезновение из предыдущего layer.',
'service-compose':'Compose-описание желаемого container: image/build, env, mounts, networks, health и restart. Это не systemd service.',
'healthcheck':'Команда, оценивающая выбранный признак внутри/рядом с service. Она доказывает только то, что действительно проверяет.',
'IAM':'Правила, связывающие identity с разрешёнными actions/resources. Долгоживущий key наследует риск своей роли.',
'cloud-init':'Bootstrap, выполняемый cloud instance при первом старте. Повторный запуск отдельных частей не всегда эквивалентен новой VM.',
'preflight':'Проверка prerequisites до side-effecting deploy. Хороший preflight завершает процесс до частично поднятой системы.',
'cutover':'Момент перевода production traffic или authority на новую среду. Требует критериев go/no-go и rollback.',
'SMTP':'Store-and-forward протокол передачи почты между clients/servers. Успешная submission ещё не доказывает final delivery.',
'DKIM':'Криптографическая подпись выбранных headers/body, проверяемая public key из DNS. В Postbox проект публикует выданные CNAME delegation records.',
'metric':'Числовое наблюдение с именем, labels и timestamp. Оно не содержит автоматически порог, приоритет или договорное обещание.',
'counter':'Metric, которая монотонно растёт до reset процесса; скорость считают через `rate`, а не вычитанием случайных точек.',
'cardinality':'Число уникальных label sets. Неограниченные user/request значения создают новые series и нагружают TSDB.',
'alert rule':'PromQL condition, labels, annotations и необязательное `for`. Alert state существует отдельно от доставки notification.',
'grouping':'Объединение alerts Alertmanager по labels для снижения шума; слишком широкая группа может скрыть отдельные impacts.',
'session':'Состояние авторизации MAX в `max.db`, функционально равное credential. Bind mount сохраняет его при recreate container.',
'backup set':'Явный перечень данных, конфигураций и ключей, необходимых для восстановления услуги. Неизвестный объект не попадает в backup автоматически.',
'RPO':'Максимальная приемлемая потеря данных, выраженная временем между последней восстановимой точкой и инцидентом.',
'RTO':'Измеренное или целевое время от начала восстановления до принятого service state.',
'migration':'Плановое перемещение системы с доступным источником и controlled cutover. Отличается от DR доступностью исходного состояния.',
'bootstrap mode':'Начальное состояние Stalwart без восстановленной рабочей конфигурации. Process может быть healthy, но service для клиента фактически потерян.',
'secret lifecycle':'Создание, хранение, выдача, использование, rotation, revocation и уничтожение credential. Пропуск offboarding оставляет orphan access.',
'least privilege':'Identity получает только actions/resources/time, необходимые задаче. Удобство не является доказательством необходимости admin role.',
'attack surface':'Все доступные интерфейсы и возможности, через которые система может быть атакована: ports, accounts, APIs, packages и supply chain.',
'break-glass':'Заранее подготовленный аварийный путь с ограниченным использованием, audit и обязательным возвратом к защищённому состоянию.',
'incident':'Незапланированный impact или существенная деградация, требующая восстановления услуги сейчас.',
'problem':'Причина или класс причин одного или нескольких incidents; работа problem management может продолжаться после восстановления.',
'change':'Контролируемое изменение состояния с owner, окном, test и rollback. Сам факт срочности не отменяет запись результата.',
'architecture decision':'Зафиксированный выбор между вариантами с requirements, trade-offs и последствиями. Это не описание уже выбранного инструмента.',
'contribution':'Revenue услуги минус её прямые переменные затраты, оценённый труд, transaction costs и reserve; источник покрытия fixed costs и прибыли.',
'margin':'Contribution / revenue. Доля не показывает абсолютный cash и чувствительна к пропущенной стоимости труда.',
'capacity':'Доступный объём работы после non-billable времени и reserve. Проданная работа не создаёт capacity.',
'WIP':'Число одновременно начатых незавершённых задач. Лимит WIP уменьшает context switching и делает очередь видимой.',
'perimeter':'Закрытый перечень объектов, операций и зависимостей, на которые распространяется услуга. Сетевая доступность не включает объект автоматически.',
'price floor':'Цена, ниже которой заданные cost и минимальная margin не выполняются. Формула при cost C и margin m: C/(1−m).',
'ICP':'Набор наблюдаемых признаков компании, при которых проблема, delivery capability и экономика одновременно подходят.',
'value proposition':'Кому, какую значимую проблему, каким результатом и с каким доказательством решает услуга относительно альтернатив.',
'stage':'Состояние сделки с проверяемыми entry/exit criteria. Выполненное продавцом действие не всегда означает переход.',
'conversion':'Доля объектов когорты, перешедших из определённой стадии в следующую; числитель и знаменатель должны быть сопоставимы.',
'discovery':'Структурированное выяснение current/desired state, impact, decision process и constraints; не бесплатное скрытое внедрение.',
'authorization':'Письменное разрешение на конкретное техническое действие, targets, время и ограничения. Наличие публичного адреса не является согласием.',
'concession':'Уступка в переговорах, обмениваемая на встречное условие. Односторонняя скидка без изменения scope уменьшает contribution.',
'BATNA':'Лучшая доступная альтернатива при отсутствии соглашения; знание BATNA предотвращает принятие разрушительной сделки.',
'MSA':'Рамочный договор с общими условиями отношений. Конкретная цена и услуга задаются Order Form и Периметром.',
'SLA reaction':'Обещанное время подтверждения и начала диагностики в определённом окне; не гарантия полного восстановления.',
'acceptance':'Формальное подтверждение, что onboarding outputs соответствуют критериям и начинается steady-state responsibility.',
'offboarding':'Управляемая передача данных/документации и отзыв доступов при завершении услуги.',
'MRR':'Нормализованная месячная повторяющаяся выручка; разовые onboarding и проекты в MRR не включаются.',
'NRR':'Отношение recurring revenue существующей когорты после churn/contraction/expansion к её начальному MRR.',
'CAC':'Согласованный набор затрат на привлечение, делённый на число новых клиентов; состав расходов должен быть стабильным.',
'LTV':'Оценка будущей contribution за жизнь клиента. В молодом бизнесе это сценарная гипотеза, а не надёжный факт.',
'capstone':'Сквозная работа без пошагового рецепта, проверяющая перенос знаний, recovery и способность обосновать решения.'}
termsets={
1:['interface','state','failure domain','evidence'],2:['evidence','interface','state'],3:['inode','permission','expansion'],4:['process','signal','unit'],5:['expansion','pipeline','process'],6:['socket','route','DNS'],7:['TLS','reverse proxy','socket'],8:['commit','index','evidence'],9:['schema','interpolation','expansion'],10:['ASGI','middleware','process'],11:['document','index-db','volume'],12:['outbox','at-least-once','idempotency'],13:['SPA','fail-closed','schema'],14:['image','namespace','cgroup','volume'],15:['build context','layer','image'],16:['service-compose','healthcheck','volume'],17:['IAM','cloud-init','route'],18:['preflight','cutover','evidence'],19:['SMTP','DKIM','bootstrap mode'],20:['metric','counter','cardinality'],21:['alert rule','grouping','session'],22:['backup set','RPO','RTO'],23:['migration','cutover','bootstrap mode'],24:['secret lifecycle','least privilege','evidence'],25:['attack surface','break-glass','least privilege'],26:['incident','problem','change'],27:['architecture decision','capstone','failure domain'],28:['contribution','margin','capacity'],29:['capacity','WIP','failure domain'],30:['perimeter','price floor','margin'],31:['ICP','value proposition','evidence'],32:['stage','conversion','WIP'],33:['discovery','authorization','evidence'],34:['concession','BATNA','margin'],35:['MSA','SLA reaction','perimeter'],36:['acceptance','offboarding','secret lifecycle'],37:['MRR','NRR','CAC','LTV'],38:['capstone','capacity','contribution','perimeter']}
internal={
1:'Проследите две независимые цепочки. В клиентской цепочке браузер доверяет DNS и TLS, Caddy выбирает route, backend валидирует payload, Mongo сохраняет заявку, а outbox доставляет её наружу. В операционной цепочке exporter публикует metric, Prometheus её забирает, rule создаёт alert, Alertmanager выбирает receiver, а MAX alerter использует сохранённую session. У этих цепочек разные состояния и разные способы доказательства.',
2:'Работайте от дешёвых read-only наблюдений к более дорогим. Сначала версия и конфигурация, затем process/socket, затем локальный request, затем внешний request. Меняйте один фактор только после фиксации baseline. Так расследование остаётся воспроизводимым, а найденная корреляция не выдаётся за причину.',
3:'При открытии `/a/b/file` kernel проверяет право прохода `x` на `/`, `/a`, `/a/b`, затем permission самого файла. Effective UID процесса определяется после `sudo`, но `*` раскрывает текущий shell раньше. Именно поэтому `sudo cat /root/x/file` работает, а `sudo cat /root/x/*` может вести себя иначе.',
4:'systemd создаёт process по ExecStart, наблюдает его exit и применяет Restart. Environment service формируется unit-файлом, EnvironmentFile и manager environment, а не вашим `.bashrc`. Journal объединяет stdout/stderr и metadata unit; фильтр `-b` ограничивает текущей загрузкой.',
5:'В строке shell сначала выполняются quotes и expansions, затем redirections, затем запускается command. В pipeline процессы стартуют параллельно. Для backup-скрипта критично различать ошибку producer и успешный `tee`; `pipefail` делает ошибку producer видимой вызывающему коду.',
6:'Диагностика идёт слоями: resolver возвращает IP; routing выбирает путь; SYN/SYN-ACK/ACK создаёт TCP; TLS проверяет имя и ключ; HTTP возвращает status; application выполняет бизнес-операцию. Перескакивание сразу к logs приложения тратит время, если SYN вообще не дошёл.',
7:'Клиентский сертификат относится к hostname, а не к адресу backend. Caddy может успешно завершить TLS и вернуть собственный 503 без обращения к FastAPI. Поэтому сравнение `curl 127.0.0.1:8001` и `curl https://domain` локализует неисправность между приложением и proxy/front door.',
8:'`git diff` без флагов сравнивает working tree с index; `git diff --cached` — index с HEAD. Review должен видеть оба. Pin версии библиотеки превращает build из «последняя доступная» в проверяемый input; обновление pin требует теста и отдельного commit.',
9:'YAML parser строит типизированное дерево, Compose проверяет допустимость ключей, затем подставляет environment и объединяет files. Только итоговая модель становится containers/networks/volumes. Поэтому `docker compose config` полезен, но его вывод может содержать подставленные secrets.',
10:'Uvicorn превращает bytes из socket в ASGI events. Middleware читает `http.request`; если body потреблён, downstream нужно вернуть его через replay. FastAPI после middleware выбирает route и валидирует model. Затем handler пишет Mongo и создаёт outbox, поэтому status ответа надо связывать с фактическим commit данных.',
11:'Mongo ACK подтверждает запись согласно write concern, но не доставку в Kaiten. Volume сохраняет database files между containers; dump создаёт переносимый logical stream. Restore в другую database позволяет проверить структуру и counts без разрушения production.',
12:'Сначала business record и outbox job должны стать durable. Worker выбирает due jobs, пытается каждый pending channel и удаляет успешный channel. Если процесс падает до удаления pending, отправка повторится; поэтому внешний вызов нуждается в stable key и deduplication.',
13:'Browser может изменить JavaScript, удалить required attribute и отправить собственный HTTP. Поэтому backend повторяет validation, consent и CAPTCHA policy. Build создаёт статические public files: любое значение, попавшее в bundle, нужно считать раскрытым.',
14:'При `docker run` kernel запускает обычный process, но Docker настраивает namespaces, cgroups, root filesystem и network. Port publishing создаёт host forwarding. Named volume монтируется поверх path внутри image: исходное содержимое этого path может стать невидимым.',
15:'Builder вычисляет cache key инструкции и её inputs. Копирование всего repository до install делает любое изменение source причиной повторной установки dependencies. Secrets нельзя исправить простым `rm` в следующем layer: предыдущий layer остаётся доступным в image history.',
16:'Compose сначала создаёт networks/volumes, затем containers. `depends_on` с health condition ждёт initial health, но после запуска backend должен сам переживать краткий отказ Mongo. External network — контракт между двумя projects и не создаётся вторым Compose автоматически.',
17:'Cloud control plane создаёт VM metadata, disk и NIC; guest cloud-init работает уже внутри VM. Ошибка guest package repository не означает ошибку создания VM. Static IP, bucket и IAM key — отдельные resources и требуют отдельного lifecycle/cost review.',
18:'Preflight уменьшает вероятность частичного deploy, но не заменяет runtime verification. После `up` отдельно проверяются process health, внутренний API, proxy, external network, alert delivery и restore. DNS переключается только когда новая среда прошла эти независимые gates.',
19:'Stalwart принимает local mail и/или отправляет через Postbox relay. Route credentials могут жить в restored RocksDB, поэтому environment не является единственным source. JMAP queue показывает recipient-level last error. После route update restart нужен, чтобы runtime перечитал состояние.',
20:'Exporter не отправляет данные в Prometheus: Prometheus сам делает scrape. Query `rate(counter[5m])` оценивает среднюю скорость с учётом reset. Histogram quantile вычисляется по агрегированным buckets; без правильного `le` и одинаковых dimensions результат бессмыслен.',
21:'Prometheus rule и Alertmanager notification — разные состояния. Alert может firing, но grouped/inhibited или receiver может падать. MAX `/health` проверяет HTTP process, auth check — session, а только тестовый alert доказывает end-to-end. Session backup должен шифроваться как пароль.',
22:'Capture выбирает согласованную точку Mongo и stateful services, restic сохраняет encrypted snapshot, `restic check` проверяет repository structure, restore materializes files. Затем приложение должно стартовать и пройти acceptance. Только последняя часть доказывает recoverability.',
23:'До cutover сравниваются counts, volume sizes, accounts, queue, health и alert delivery. DNS меняет только имя→IP, но не переносит данные. Observation window сохраняет старую VM доступной для rollback; её нельзя удалять сразу после первого 200.',
24:'Secret появляется при generation и должен иметь owner/purpose/expiry. Vault sharing выдаёт доступ identity; запись в access matrix объясняет основание. При offboarding сначала revoke, затем rotation shared credentials, затем проверка logs. Удаление карточки пользователя без rotation может оставить ранее скопированный секрет рабочим.',
25:'Закрытие 22 выполняется как change с двумя каналами доступа. Сначала VPN connection и SSH по private address, затем ufw, затем SG, затем внешний negative test. Break-glass правило открывается временно, ограничивается адресом по возможности и удаляется после ремонта.',
26:'Incident lead управляет приоритетом и коммуникацией, technical responder меняет систему, scribe ведёт timeline. После recovery problem analysis проверяет гипотезы evidence. Preventive action должна менять code/config/process и иметь test, иначе это пожелание.',
27:'В capstone сначала фиксируются requirements: число пользователей, допустимый downtime, данные, угрозы и budget. Только затем выбираются components. Замена Mongo на PostgreSQL допустима, если перепроектированы schema, backup, health и application access, а не просто изменено имя image.',
28:'Месячная модель отделяет recurring subscription, onboarding и pass-through. В каждом cost есть формула: часы×ставка, процент банка, налоговая база, storage units. Sensitivity показывает, какая переменная разрушает margin первой; обычно это незамеченные часы и incidents.',
29:'Для двух человек calendar availability нельзя целиком продавать клиентам. Reserve покрывает случайные P1, обучение и болезнь. Forecast строится по пакетным включённым часам плюс фактическому distribution, а не только среднему: один тяжёлый месяц способен нарушить SLA.',
30:'Сначала технический perimeter задаёт objects и criticality, затем workload estimate и dependencies. Price floor вычисляется из cost и margin requirement. Пакет — удобная оболочка, но исключения и pass-through защищают от неизвестного storage, лицензий и migration debt.',
31:'ICP формулируется через проверяемые признаки: страна/тип бизнеса, размер контура, наличие ответственного, зрелость доступа и способность оплатить. Pain подтверждается интервью и поведением, а не приписывается компании по отрасли. Anti-ICP экономит capacity.',
32:'Карточка входит в stage только после entry facts и выходит после customer commitment. Pipeline review ищет age, missing next action и reason. Gold добавляет capacity check между proposal и contract: коммерческое желание не обходит операционный gate.',
33:'Вопросы discovery идут от бизнес-impact к технической структуре. Claim клиента записывается с источником. Unknown не заполняется догадкой. Если нужен scan, отдельный authorization фиксирует targets, source IP, время, методы и контакт остановки.',
34:'Переговоры меняют несколько переменных: scope, срок, цена, payment timing и risk. Ответ на «дорого» начинается с уточнения сравнения. Скидка моделируется в contribution, а не только проценте revenue. 24/7 требует staffing, поэтому не может быть бесплатной строкой.',
35:'Договорные документы должны ссылаться на один и тот же perimeter и package. SLA clock зависит от регистрации и окна, pauses — от ожидания клиента. DPA описывает роль оператора/обработчика и данные; шаблон не заменяет проверку юристом РФ.',
36:'После Won sales передаёт не обещания в чате, а подписанный scope и contacts. Onboarding создаёт baseline и список open risks. Acceptance отделяет внедрение от recurring service. Offboarding зеркально удаляет доступ, передаёт artifacts и учитывает retention backups.',
37:'Dashboard начинается со словаря метрик. Для каждой фиксируются source tables, formula, period, cohort и action threshold. Revenue metrics сравниваются с contribution и capacity; иначе рост MRR может маскировать убыточную перегрузку.',
38:'Decision pack должен быть воспроизводим: другой reviewer пересчитывает effort, price и margin из inputs. Unknowns превращаются в conditions или paid assessment. Итог accept/waitlist/no-fit защищает существующих клиентов и не подменяется желанием закрыть продажу.'}

def command_explain(line):
 s=line.strip()
 if not s or s.startswith(('#','flowchart','U[','C -->','B -->','P[','A -->','services:','backend:','mongo:','handle ','root ','file_server','FROM ','WORKDIR','COPY ','RUN ','CMD ','Object:','Пустая ','ICP ','New ','Won ')): return None
 rules=[
 ('sudo ','`sudo` запускает следующую программу с повышенной effective identity; shell уже обработал кавычки, glob и redirection.'),
 ('docker exec','`docker exec` создаёт новый process в namespaces работающего container; это не новый container и не проверка restart path.'),
 ('docker compose config','Команда строит итоговую Compose-модель после interpolation и merge; она не запускает services.'),
 ('docker compose up','`up` приводит runtime к описанной модели; `-d` отсоединяет terminal, `--force-recreate` пересоздаёт container.'),
 ('curl ','`curl` создаёт реальный HTTP/TLS request. `-f` делает HTTP 4xx/5xx ненулевым exit, `-sS` скрывает progress, но оставляет ошибки.'),
 ('git ','Git-команда читает или изменяет working tree/index/refs; перед mutation сравните `status` и `diff`.'),
 ('systemctl ','`systemctl` обращается к systemd manager; `status` показывает unit state и последние сообщения, но не внешний user path.'),
 ('journalctl ','`journalctl` читает structured journal; `-u` фильтрует unit, `-b` — boot, `-n` — последние записи.'),
 ('restic ','Restic-команда работает с repository из environment; `snapshots/check/restore` отвечают на разные вопросы и не взаимозаменяемы.'),
 ('mongodump','`mongodump` создаёт logical BSON dump; `--archive --gzip` формирует один сжатый stream.'),
 ('mongorestore','`mongorestore` записывает данные в target; `--drop` удаляет существующие collections и требует отдельного подтверждения.'),
 ('ss ','`ss -lntp` показывает listening TCP sockets, numeric addresses и process metadata при достаточных правах.'),
 ('dig ','`dig` спрашивает DNS; `+short` удобен, но скрывает TTL, authority и response code.'),
 ('nc ','`nc -vz` проверяет установление TCP без application protocol; успех не означает корректный HTTP/TLS.'),
 ('yc ','`yc` вызывает cloud control plane от identity текущего profile; ресурсы и billing создаются вне VM.'),
 ('chmod ','`chmod` изменяет permission bits; он не меняет владельца и не отзывает уже скопированный secret.'),
 ('openssl ','`openssl rand -hex 32` получает 32 random bytes и печатает 64 hex-символа; вывод нужно сразу хранить защищённо.'),
 ('set -','Shell options меняют обработку ошибок текущего script; они не превращают каждую логическую ошибку в ненулевой exit.'),
 ('rate(','`rate` оценивает скорость counter по диапазону и учитывает reset; instant selector counter показывает накопленное значение.'),
 ('histogram_quantile','Функция оценивает quantile из cumulative buckets; aggregation обязана сохранить label `le`.'),
 ]
 for k,v in rules:
  if k in s: return v
 if s.startswith(('$','- ','|')): return 'Эта строка является частью конфигурации или формулы; смысл определяется родительским блоком и отступом.'
 return 'Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.'

for f in sorted(C.glob('*.md')):
 n=int(f.name[:2]); t=f.read_text()
 terms=['## Термины в рабочем смысле','']
 for x in termsets[n]: terms += [f'### {x}','',defs[x],'']
 block='\n'.join(terms)+f'\n## Что происходит внутри\n\n{internal[n]}\n'
 t=t.replace('## Разобранный пример',block+'\n## Разобранный пример',1)
 # Replace generic line explanation bullets
 lines=t.splitlines(); out=[]
 for line in lines:
  if line.startswith('- `') and 'найдите в документации владельца синтаксиса' in line:
   code=line.split('`',2)[1]; exp=command_explain(code); out.append(f'- `{code}` — {exp}')
  else: out.append(line)
 f.write_text('\n'.join(out),encoding='utf-8')
print('ENHANCED',len(list(C.glob('*.md'))))
