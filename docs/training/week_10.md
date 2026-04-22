# Week 10 · Incident response в deep-dive

## Цель

Самостоятельно вести P2 инциденты от alert до closure + post-mortem.

## Задачи

- [ ] Перечитать R-01..R-11.
- [ ] Сессия с owner: как ставить приоритеты при 2+ одновременных
      инцидентах.
- [ ] Напиши с нуля свой runbook (R-12 — предложить тему: например,
      «Зависание PostgreSQL»). Выложи на review в MR.

## Production

- [ ] Взять следующий P2 один (с owner на pre-warned standby).
- [ ] Написать post-mortem по post_mortem_template.

## Read

- `docs/post_mortem_template.md` — перечитать до автоматизма.
- [Google SRE Book · "Managing Incidents"](https://sre.google/sre-book/managing-incidents/).

## Check-in

1. Как ты решаешь, какой из 2 P2 брать первым?
2. Что значит blameless post-mortem?
3. Как выглядит escalation process, если ты залип?

## DoD

- Взял 1+ P2 один (с backup).
- Написал 1 post-mortem (принят).
- Написал 1 новый runbook (принят).
