# Структура репозитория и архив

## Где искать и куда добавлять

| Направление | Вход | Фактическое хранение |
|---|---|---|
| Маркетинг | [`marketing/README.md`](../marketing/README.md) | канонические цены/продажи в `commercial/`; архив контента в `marketing/arhive/` |
| Разработка | [`development/README.md`](../development/README.md) | `backend/`, `frontend/`, `services/`, `scripts/`, `deploy/`, `migration/` |
| Документация | [`docs/README.md`](README.md) | deployment, operations, onboarding, runbooks, checklists, training |
| Договор | [`contracts/README.md`](../contracts/README.md) | один MSA и DOCX builder; v2 — `contracts/arhive/v2/` |
| Учебный Wazuh | [`training/wazuh/README.md`](training/wazuh/README.md) | курс — в docs, исполняемый комплект — `deploy/wazuh-lab/` |

Имена технических путей оставлены латиницей для совместимости с Docker/CI/Linux. Три русскоязычных входа в корневом README служат рабочей структурой; переносить код под новый физический root без миграции build contexts, imports, bind mounts, scripts и VM нельзя. Документы и код не дублируются ради новой витрины.

## Что перемещено 15.10.2026

- `analysis/*.md` (старые CAC/LTV/рынок/экономика) → `analysis/arhive/`.
- Старые `marketing/01…06`, `articles/`, `lead_magnets/`, seed CSV → `marketing/arhive/`.
- `contracts/v2/` → `contracts/arhive/v2/`.
- Старые sales scripts/templates → `docs/arhive/sales/`; прежний `docs/sales/README.md` оставлен маршрутом совместимости.
- Аудиты v4/v5/июнь и v4 roadmap → `docs/arhive/audit/`, `docs/arhive/roadmap/`.
- Старый hardcoded watcher → `docs/arhive/vwautostart/`; текущий — `services/vm_watcher/`.
- Сентябрьский commercial analysis → `commercial/arhive/ANALYSIS_2026-09.md`.

`arhive` написано так по выбранному владельцем имени. Не создавать пустые архивы в каждом каталоге: они появляются при наличии реально выведенного материала. Учебные/альтернативные контуры не архивируются только из-за возраста или отсутствия production.

## Правила актуальности

1. Один канонический источник; индекс ссылается на него, не копирует содержимое.
2. При переносе сохранять содержание/историю, обновлять входящие ссылки. Архивный README указывает замену и дату; исторические команды не выполнять.
3. Архив не источник оффера, SLA, секретов или production inventory. Известные старые пути в changelog обозначают историю, не действующие ссылки.
4. Книгу `book/` читать как дополнительный учебник: встроенные срезы коммерческих документов могут устаревать; текущий прайс, курс и runbook выше по приоритету.
5. Три состояния независимы: файлы на workstation, опубликованный GitHub commit, реально применённая VM. В change record указывать, что именно обновлено.

Проверки: [разработка](../development/README.md). Изменения репозитория не выполняют deployment автоматически.
