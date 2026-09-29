# 30. Из технического границы услуги в пакет и цену

> **Учебная ситуация.** Клиент просит «всё администрирование», но такой границы услуги нельзя оценить и принять.

## Главное

Периметр превращает абстрактную поддержку в перечень объектов, критичности, разрешённых действий и зависимостей.

Цена строится снизу: труд + переменные расходы + reserve + целевая вклад в покрытие. Пакет упрощает продажу, но Order Form уточняет реальный границы услуги.

Discount уменьшает вклад в покрытие на полный размер скидки. Скидка оправдана только встречным улучшением: prepayment, срок, меньший границы услуги.

## Как это работает

Сначала технический perimeter задаёт objects и criticality, затем workload estimate и dependencies. Price floor вычисляется из cost и рентабельность requirement. Пакет — удобная оболочка, но исключения и перевыставляемые расходы защищают от неизвестного storage, лицензий и migration debt.

## Пример

```text
Минимальная цена при cost=18 250 и рентабельность floor=50%:
price = cost / (1 − 0,50) = 36 500 ₽
```

## Практикум

1. Соберите perimeter учебного клиента.
2. Оцените часы и reserve.
3. Сравните Bronze/Silver/custom и проверьте скидку.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Пакет выбран только по числу VM | игнорируются criticality/dependencies. |
| Gold 120k ниже floor после ротации | повысить цену или изменить границы услуги. |

## Источники проекта

- [commercial/PRICING.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/commercial/PRICING.md)
- [technical/1_Bronze/Bronze.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/technical/1_Bronze/Bronze.md)
- [technical/2_Silver/Silver.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/technical/2_Silver/Silver.md)
- [technical/3_Gold/Gold.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/technical/3_Gold/Gold.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

