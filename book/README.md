# Книга владельца и начинающего маркетолога

Начните с [маршрута своего читателя](READING_PATHS.md), затем откройте [учебник из 22 глав](BOOK.md). [Текущая картина](CURRENT_STATE.md) отличает работающий код, подтверждённые проверки и открытые вопросы.

- [Бизнес-процессы](PROCESS_MAP.md): участники, входы, передача и результат.
- [Инструменты и углублённое обучение](STACK_AND_LEARNING.md).
- [Видеоуроки и официальные записи](VIDEO_GUIDE.md), с языком, границами проверки и практикой.
- [Клиентский стек и российское ПО](CLIENT_STACK_ACADEMY.md): 1С, AD, почта/DNS, файлы, БД, Loki/Puppet и ОС; точный статус видеоматериалов.
- [Управление, клиентские разговоры и продажи](MANAGEMENT_PRACTICE.md): техники, ролевые ситуации и план первого запуска.
- [Словарь](GLOSSARY.md), [цена и мощность](TARIFF_DECISION.md), [источники](SOURCE_MAP.md).

## Изменение книги

Редактируются `lessons/*.md` и `curriculum.json`; `chapters/`, `BOOK.md`, `SOURCE_MAP.md`, `manifest.json` собираются командой `python book/build_deep_book.py`. Сборщик не удаляет неизвестные файлы и не переписывает проверяющие скрипты. Прежняя книга с вставками исходников — [arhive](arhive/README.md).

Проверки: `python book/verify_deep_book.py`, `python book/verify_readability.py`, `python scripts/validate_markdown_links.py`. Сверять [правила текста](NATURAL_WRITING_SKILL.md). Книга объясняет; production-команды выполняются только по текущему профильному runbook с разрешением.
