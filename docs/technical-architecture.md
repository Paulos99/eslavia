# Техническая архитектура

## Стек

- Vite + React 18 + TypeScript
- CSS custom properties (`src/styles/tokens.css`), без Tailwind
- React Router: `/` и `/privacy`
- Иконки: lucide-react
- Анимации: CSS + IntersectionObserver, без Framer Motion
- Сервер заявок: Node (`server/index.mjs`) — `POST /api/wholesale-lead` → FormSubmit / Яндекс.Почта

## Принцип

`data ≠ UI`. Каталог читается из `data/*.json`. Компоненты только отображают.

```
src/
  components/   UI-блоки секций
  data/         реэкспорт JSON
  hooks/        useProducts, useFilters, useModal, useReducedMotion
  lib/          submitLead, formatPrice
  styles/       tokens.css, globals.css
server/         email lead API (FormSubmit)
public/images/products/<id>/01.webp
public/prices/optovyy-prays.pdf
```

## Состояние

Локальный React state. Фильтры — в хуке, модал — выбранный product id. Без Redux.

## Изображения

WebP, width/height 3:4, `loading="lazy"` кроме hero и первых двух карточек. `srcSet` не обязателен при одном размере файла ~800px по длинной стороне.

## Форма опта

Клиент вызывает `submitLead`.  
Прод (GitHub Pages): браузер шлёт письмо через FormSubmit на адрес из `data/lead-mail.json`.  
Локально / свой Node: `POST /api/wholesale-lead` → `server/mail.mjs`.  
`LEAD_ADAPTER=mock` — только local dev.  
Успех → показать кнопку PDF `/prices/optovyy-prays.pdf`. Ошибка → текст ошибки, PDF не открывать.

## SEO

`index.html`: title, description, OG, canonical.  
`public/robots.txt`, `public/sitemap.xml`, favicon.

## Доступность

Семантика секций и заголовков, focus-visible, focus trap в modal, Escape, alt у фото (название + артикул).
