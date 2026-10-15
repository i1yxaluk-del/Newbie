# Аудит тарифов, воронки, рекламы и договоров

Дата: 2026-09-24.

## Вывод

Оставлен один commercial pack и один договор. Все три тарифа — Bronze, Silver и Gold — работают в обычной продаже.

## Тарифы

Тарифы: Bronze 25 000 ₽, Silver 50 000 ₽, Gold 85 000 ₽. Gold включает SIEM Wazuh + Kaspersky Security, контроль уязвимостей (CVE-скан), SLA-отчёты с метриками и квартальный DR-drill; состав и окно реакции фиксируются в Order Form.

Убраны дешёвые addons, юридический compliance как работа инженера, бесплатный месяц и ручные скидки 20%. Стандартная скидка — до 5% за годовую предоплату; для Gold первые три месяца скидки нет.

## Воронка

Воронка единая для всех трёх тарифов: New → Qualified → Discovery → Proposal → Contract → Won. Состав Gold (SIEM, DR, окно реакции) уточняется на этапе Discovery.

## Реклама

Gold упоминается как тариф от 85 000 ₽/мес (SIEM Wazuh + Kaspersky, DR-drill). Не обещаем круглосуточную реакцию без отдельного согласования. Основной публичный оффер строится вокруг monitoring и restore evidence.

## Договор

Единый договор содержит Order Form, SLA, Периметр, DPA и акт. Gold добавлен в Order Form и SLA как стандартный тариф: режим покрытия и состав (SIEM, DR) фиксируются в Order Form.

Из старого v2 сохранены scope, права/обязанности, приёмка, оплата, SLA, service credits, DPA, IP, ответственность и offboarding. Не перенесены спорные автоматическая приёмка, 14-дневный cutoff требований, налоговый регресс и чрезмерные NDA/force-majeure штрафы.

## Итоговая структура

`commercial/PRICING.md`, `SALES_FUNNEL.md`, `SALES_PLAYBOOK.md`, `ADS.md`, `PROPOSAL.md`, единый `contracts/MSP_SERVICE_AGREEMENT.md` и CI artifact `current-contract-docx`.

Перед первой подписью, особенно Gold, обязательна проверка практикующим юристом РФ.
