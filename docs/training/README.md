# 12-недельная программа обучения · Junior MSP Engineer

## Философия

1. **50% времени первые 2 недели — в паре с тобой (owner).** После
   этого — самостоятельная работа под supervision, еженедельные
   retrospectives.
2. **Не learn-by-drinking-from-firehose.** Никаких «прочитай эту книгу
   на выходных». Всё обучение встроено в рабочие задачи.
3. **По неделям:** каждая неделя = 1 основная тема + повседневные
   задачи. В конце недели — 15-минутный check-in.
4. **Выход из испытательного:** через 12 недель должен уверенно вести
   P2/P3 один, понимать архитектуру, уметь отвечать клиенту.

## Итоговый тест (месяц 4)

По завершении 12 недель — **проверка под нагрузкой**:
- 1 день недели полностью один на P2/P3 тикетах.
- Weekly-sync с клиентом ведёт junior, owner слушает.
- Написание одной главы runbook'а с нуля.

## Расписание

| Week | Theme | File |
|---:|---|---|
| 1 | Онбординг + tooling | [week_01.md](week_01.md) |
| 2 | Linux deep-dive + our baseline | [week_02.md](week_02.md) |
| 3 | Monitoring (Prometheus + Grafana) | [week_03.md](week_03.md) |
| 4 | Backup & Recovery (restic + DR) | [week_04.md](week_04.md) |
| 5 | Networking + WireGuard | [week_05.md](week_05.md) |
| 6 | Security (hardening, SIEM basics) | [week_06.md](week_06.md) |
| 7 | Active Directory + GPO | [week_07.md](week_07.md) |
| 8 | 1С и специфика РФ | [week_08.md](week_08.md) |
| 9 | Ansible + Infrastructure-as-Code | [week_09.md](week_09.md) |
| 10 | Incident response в deep-dive | [week_10.md](week_10.md) |
| 11 | Communication + customer success | [week_11.md](week_11.md) |
| 12 | Go-live + самостоятельная неделя | [week_12.md](week_12.md) |

## Ресурсы (read if/when needed, not all at once)

- *The Site Reliability Workbook* — Google SRE (выборочно: главы 1, 6, 8, 11).
- *Linux Bible* (Negus) — справочник, не учебник.
- Официальная документация: Ansible, Prometheus, restic.
- Наш internal wiki (`docs/`).

## Правила compensation time

- 1 час в неделю — «личное обучение» вне задач (курсы, YouTube, чтение).
- 1 час в неделю — pairing-звонок с senior (вопросы, ретро).
- Не более 40 часов в неделю суммарно.
