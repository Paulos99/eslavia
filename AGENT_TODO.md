# Сделать утром (агент на ПК с `yc`)

Код фикса уже в `main`. Нужен только деплой бэкенда кабинета.

## Задача

Перевыложить Cloud Function **`eslavia-admin-api`** (id `d4erap1jhoq7skqs7c7e`, каталог `eslavia`) из `tools/admin-api/`.

Без этого на проде останется старая валидация: сохранение карточки в новой категории (например «Толстовки») падает на «Готовим фото» с текстом «Выберите категорию из списка».

## Шаги

1. `git pull` на `main`.
2. Снять параметры текущей версии:  
   `yc serverless function version list --function-name=eslavia-admin-api`  
   и `yc serverless function version get <id-последней>` — runtime, entrypoint, memory, timeout, service account, env, Lockbox.
3. Создать новую версию из `tools/admin-api/` **с теми же параметрами** (entrypoint `index.handler`), только свежий source.
4. Проверка: в кабинете https://eslavia.ru/admin/ открыть модель в «Толстовки», сохранить с фото — шаг «Готовим фото» должен пройти.
5. Удалить этот файл (`AGENT_TODO.md`) и закоммитить удаление в `main`.

## Контекст фикса

В `pipeline.clean_product` категория сверялась с захардкоженным списком, а не с `data/categories.json`. Теперь `save()` передаёт живой список категорий из репозитория.
