# Кабинет администратора

Адрес: https://eslavia.ru/admin/ (вход по паролю, страница закрыта от поисковиков).

Сохранение товара одним коммитом обновляет data/products.json, data/categories.json,
фото товара, оптовый прайс (PDF), каталог Mini App и пост в канале @eslavia_opt.

Бэкенд: Yandex Cloud, каталог `eslavia`: функция `eslavia-admin-api`, API Gateway
`eslavia-admin-gw`, секреты в Lockbox `eslavia-admin`. Исходники функции: tools/admin-api/.

Служебные данные: data/tg-posts.json (связь товар → сообщения в канале),
data/price-thumbs/ (миниатюры для прайса).
