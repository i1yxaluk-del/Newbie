# Контент из VK-группы

Группа: https://vk.ru/gostevoy_domalina
Личная страница руководителя: https://vk.ru/id135593764
Фото руководителя: https://vk.ru/photo135593764_457241091
Контакт: +7 918 212-96-01, Лукьянченко Александр Викторович

## Что нужно перенести руками (быстро)
1. **Фото гостевого дома** — скачать 8–12 лучших из альбомов группы, сложить в `Domik/frontend/public/img/gallery/01.jpg ... 12.jpg`. В компоненте `Landing.jsx` секцию `gallery` заменить плейсхолдеры на `<img src="/img/gallery/01.jpg" />`.
2. **Адрес** — из раздела «Контакты» группы → внести через `/admin/landing-edit` в ключ `location.address`.
3. **Фото руководителя** — скачать с https://vk.ru/photo135593764_457241091, положить как `Domik/frontend/public/img/owner.jpg`. В `Landing.jsx` заменить `<div className="owner__avatar">АЛ</div>` на `<img className="owner__avatar" src="/img/owner.jpg" />`.
4. **Описания номеров/удобств** — внести в `/admin/landing-edit`.

## Что можно автоматизировать позже
- VK API (метод `photos.get`) для автоподтяжки фото из публичных альбомов.
- Парсинг постов группы (метод `wall.get`) с показом «Последние новости» на лендинге.
