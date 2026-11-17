# Кабинет администратора

Адрес: https://eslavia.ru/admin/ (вход по паролю, страница закрыта от поисковиков).

Сохранение товара одним коммитом обновляет data/products.json, data/categories.json,
фото товара, оптовый прайс (PDF), каталог Mini App и пост в канале @eslavia_opt.

Бэкенд: Yandex Cloud, каталог `eslavia`: функция `eslavia-admin-api`, API Gateway
`eslavia-admin-gw`, секреты в Lockbox `eslavia-admin`. Исходники функции: tools/admin-api/.

Служебные данные: data/tg-posts.json (связь товар → сообщения в канале),
data/price-thumbs/ (миниатюры для прайса).

Таблица Excel: «Скачать таблицу» (/export) выгружает весь каталог, «Загрузить таблицу» показывает
разницу (/import-preview) и применяет её одним коммитом (/import-apply). Строки, которых нет в таблице,
удаляются только после отдельного подтверждения. «Скачать прайс» (/pdf) отдаёт PDF из репозитория.

Telegram: из Yandex Cloud Functions api.telegram.org недоступен (соединение режется по пути, проверено
17.11.2026). Поэтому перед коммитом функция проверяет связь (getMe), а неотправленные обновления постов
кладёт в data/tg-queue.json тем же коммитом. Отправить очередь: кнопка «Отправить ещё раз» в кабинете
(сработает, если связь появится) или с машины, где Telegram открывается:
`GITHUB_TOKEN=... TG_TOKEN_FILE=~/.secrets/eslavia_opt_bot.token python tools/admin-api/flush_tg_queue.py`.
