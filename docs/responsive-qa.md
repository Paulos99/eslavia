# Responsive QA

Проверено кодом, сборкой и HTTP-смоуком на `http://127.0.0.1:4173`. Живой браузерный MCP в этой сессии был недоступен; визуал карточек сверен по исходным WebP.

## Брейкпоинты (CSS)

| Ширина | Сетка каталога | Header | Фильтры |
|---|---|---|---|
| 320–374 | 2 колонки, уменьшенный CTA | лого + CTA 13px + burger | bottom sheet |
| 375–430 | 2 колонки | то же | sheet |
| 768 | 3 колонки | горизонтальное меню с 900px | desktop chips |
| 1024+ | 4 колонки | полное меню + CTA | desktop bar |
| 1280–1440 | контейнер 1280 | sticky blur | без overflow |

## Проверено в вёрстке

- Touch target кнопок/чипов/меню: min-height 44px
- Таблица размеров: horizontal scroll на узком экране
- Modal: 100% ширины на mobile, drawer 560px на desktop
- `prefers-reduced-motion` отключает transform
- Нет горизонтального overflow у контейнера (`100% - 32/48px`)

## Смоук

- `/` 200
- `/privacy` 200 (SPA fallback)
- `/prices/optovyy-prays.pdf` 200, PDF
- карточка WebP 200
- `POST /api/wholesale-lead` mock ok при согласии; 502 без согласия
