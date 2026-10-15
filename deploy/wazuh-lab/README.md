# Wazuh: изолированный учебный контур Junior

## Фактически развёрнуто 15.10.2026

- Astra Linux 1.8 x86-64, локальная VM `192.168.114.10`, 32 vCPU / 32 ГБ RAM.
- Wazuh manager, indexer, dashboard **4.14.5**, отдельный проект `msp-wazuh-lab`.
- Dashboard: **https://192.168.114.10** (локальная сеть/VPN), пользователь `admin`.
- Пароли сгенерированы, известные upstream demo passwords заменены. Получить пароль через приватную операторскую сессию из root-only `/home/service/wazuh-lab/credentials.json` и перенести в vault; не вставлять в Git/тикет/чат. SSH-пароль VM не является паролем Wazuh.
- TLS — учебный CA. Проверить fingerprint с оператором и импортировать CA на учебную станцию; не отключать TLS-проверку браузера глобально. Сертификат upstream создан для имени dashboard; для постоянного доступа по IP требуется перевыпуск с IP SAN либо локальное DNS-имя с подходящим сертификатом.
- Indexer `9200` и manager API `55000` опубликованы только на loopback. TCP `1514` — на локальном IP для будущих учебных агентов. Enrollment `1515` отключён; подключения клиентских production agents не настроены.
- State: `/home/service/wazuh-lab/data/`, synthetic fixtures: `training/`; Docker images — существующий `/var/lib/docker`.
- Существующие `lt` и `mspshield-mongo` не пересоздавались. Host change: `vm.max_map_count=262144`, отдельный sysctl-файл; установлен `python3-bcrypt`. Compose 2.39.4 находится только в `wazuh-lab/tools/`, системный Compose 1 не заменён.

Astra не находится в рекомендованном списке ОС Quickstart Wazuh. Проверена именно контейнерная лаборатория, не нативная установка или поддержка/сертификация Astra. Контейнерная SCA оценивает ОС контейнера (Amazon Linux), а не Astra-host. Это важно при разборе отчётов junior.

## Ресурсы

### Русский интерфейс (частичный локальный перевод)

Применён `i18n.locale: ru-RU` и локальный каталог `ru-RU.json` (61 сообщение оболочки: кнопки, интервалы времени, таблицы, уведомления). Регистрация через `.i18nrc.json` Wazuh Core и bind mounts сохраняет перевод после recreate dashboard. Проверены `/translations/ru-RU.json` (61 сообщение, warning=null) и login HTTP 200. Перезапускался только dashboard.

Для главной страницы Wazuh дополнительно применён `wazuh-home-ru.js`: точные переводы предоставленных владельцем заголовков, карточек, важности и сообщения об отсутствии агентов. Подключение — version-checked template mount через `apply_home_translation.py`, локальный same-origin JS без изменения CSP и внешних сервисов. Поддерживает динамическую отрисовку; поля ввода, код и raw document viewer исключены. Проверены DOM-преобразование, включение script в HTML и HTTP-доступность asset. Визуальная приёмка в авторизованном браузере остаётся обязательной.

Это не полный официальный перевод Wazuh: остальные разделы без i18n и описания встроенных правил могут оставаться английскими. Синтетические правила lab уже имеют русские описания. Применение: `sudo python3 apply_locale.py ru-RU.json`, затем `sudo python3 apply_home_translation.py wazuh-home-ru.js`; backup compose/config — `locale-backups/<UTC>/`. После обновления образа перепроверить совместимость ключей/template. Для отката вернуть compose/config из первого backup до русификации и пересоздать только dashboard. В браузере после применения — Ctrl+F5.

[Официальный Quickstart](https://documentation.wazuh.com/current/quickstart.html): для 1–25 агентов ориентир 4 vCPU / 8 GiB / 50 GB. На Astra достаточно CPU/RAM и >200 ГБ свободно на `/home`; после загрузки образов на `/` осталось около 8,5 ГБ. Следить за `/`: рост image layers/logs может заполнить root, даже когда `/home` свободен. Не выполнять глобальный `docker system prune` на общей машине.

Лимиты контейнеров: manager 3 GiB, indexer 4 GiB, dashboard 2 GiB, до 4 CPU каждому. Java heap indexer 1 GiB. Для малой лаборатории это стартовая конфигурация, не sizing клиента. Retention индексов и ежедневный контроль диска обязательны перед регулярной генерацией большого числа событий; автоматического удаления индексов в этом комплекте нет.

## Воспроизведение

1. Чистый выделенный каталог, 50 GiB свободно на `/home`, ≥10 GiB для Docker images, ≥8 GiB доступной RAM; свободны 443/1514/loopback 9200/55000. Сверить SSH host key, существующие контейнеры и маршруты.
2. Нужны Docker, Git, curl, `python3-yaml`, `python3-bcrypt`. Не обновлять всю ОС/перезапускать Docker ради lab.
3. `sudo python3 prepare.py --host-ip <LAN_IP>` клонирует upstream tag `v4.14.5`, фиксирует commit в manifest, создаёт secrets/config/bind data. Повторный запуск в существующий каталог запрещён.
4. Установить официальный standalone Compose **2.39.4** в `/home/service/wazuh-lab/tools/docker-compose`, проверить его checksum по release. Compose 1.29 на этой Astra не работает с текущим requests (`http+docker`), не понижать системные Python-пакеты ради него.
5. `sudo python3 start.py`: sysctl, `config --quiet`, генерация TLS, запуск только lab. Изменение host sysctl зафиксировано отдельно; firewall/Docker daemon не меняются.
6. Установить `local_rules.xml` как `/var/ossec/etc/rules/msp_lab_rules.xml` в manager (owner `wazuh:wazuh`, mode 0640), выполнить `/var/ossec/bin/wazuh-analysisd -t`, затем перезапустить только manager.
7. `sudo python3 generate_events.py`, подождать индексацию, `sudo python3 verify.py`. Ожидается green/yellow indexer, HTTP 302 login, indexed synthetic alerts ≥4. Проверять поле `data.run_id`, не только общий счётчик.

`start.py` — bootstrap: не выполнять заново для обычного restart, чтобы не перевыпускать TLS. Подготовленные effective config содержат secrets и остаются только на VM.

## Управление

```bash
cd /home/service/wazuh-lab/upstream/single-node
sudo /home/service/wazuh-lab/tools/docker-compose -p msp-wazuh-lab ps
sudo /home/service/wazuh-lab/tools/docker-compose -p msp-wazuh-lab stop
sudo /home/service/wazuh-lab/tools/docker-compose -p msp-wazuh-lab start
```

Не применять `down -v` или удаление `data/` как способ исправить вход. При изменении — backup конфигурации, сертификатов и state с остановленным только lab, проверка восстановления на другом стенде. Backup лаборатории пока не включён в production restic.

## Учебная программа

| Уровень | Модули/данные | Практика и критерий |
|---|---|---|
| Базовый | JSON decoder, custom rules 100100–100103, manager→Filebeat→indexer→dashboard | Найти `rule.groups:msp_lab`, разобрать baseline/backup_failed/access_review/policy_drift, показать raw event и правило, объяснить synthetic label |
| Базовый | FIM, realtime `/var/ossec/lab/fim` | Изменить только `training/fim/training-policy.txt`, найти изменение, отличить FIM от события JSONL; сверить baseline scan |
| Базовый | Syscollector и SCA включены | Найти inventory и SCA, объяснить что ОС контейнера ≠ Astra, не исправлять host по контейнерному CIS автоматически |
| Расширенный | Vulnerability detection включён, indexer connector | Проверить получение feed/состояние inventory. Отсутствие CVE не считать доказательством безопасности; импорт учебного JSON не является настоящим CVE scan |
| Расширенный следующий этап | Отдельные Linux/Windows учебные agents, Windows EventChannel/Sysmon, auditd, tenant groups | Требуются отдельные endpoints, согласование enrollment и персональные read-only роли. Не установлены на Astra-host этим rollout; не подключать клиента по умолчанию |
| Проект клиента | TLS, RBAC, tenant isolation, retention, sizing, backup/DR, лицензии/поручение | Предоставить архитектуру и evidence, затем pilot. Kaspersky/EDR — отдельная лицензия/интеграция, не установленный автоматически модуль Wazuh |

Active Response и автоматические блокировки не активированы. Синтетические события не запускают атаки, brute force, malware, сканирование или изменение firewall. По завершении упражнения junior сдаёт timeline, правило/поля, критерий ложного срабатывания, эскалацию и ограничения вывода. Допуск к клиенту — отдельно по [`BRONZE_EXAM.md`](../../docs/training/BRONZE_EXAM.md).
