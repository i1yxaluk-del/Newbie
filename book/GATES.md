# Границы готовности полной редакции

- [ ] G1: В каждой главе нет старых шаблонных разделов и бессмысленного разбора команд.
  CHECK: `python book/verify_readability.py`
  EXPECT: `BOOK READABILITY OK`
- [ ] G2: Глава Yandex Cloud объясняет базовые сущности до команд и содержит практику и видео.
  CHECK: `python book/verify_readability.py --yandex`
  EXPECT: `YANDEX CHAPTER OK`
- [ ] G3: Оглавление, карта связности и правила языка согласованы.
  CHECK: `python scripts/validate_markdown_links.py`
  EXPECT: `MARKDOWN NAVIGATION OK`
