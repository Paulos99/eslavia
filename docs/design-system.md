# Дизайн-система — Таисия

Язык: modern fashion-catalog / Russian apparel brand / clean editorial commerce.  
Не копировать OpenCart-витрину.

## Цвет

Один акцент — припылённый терракотовый, спокойный и «тканевый».

```css
--background: #F7F5F1;
--surface: #FFFCFA;
--text: #181716;
--muted: #77736E;
--line: #E4DFD6;
--accent: #9A5B45;
--accent-hover: #824C3A;
--focus: #181716;
```

Контраст текста на фоне: тёмный на off-white. Акцентные кнопки: белый текст на `#9A5B45`.

## Типографика

- UI / body: **Manrope**
- Заголовки секций и hero: **Cormorant Garamond** (кириллица)

Шкала desktop:

- Hero: 72px / 1.05
- Section: 48px
- Product title: 20px
- Body: 17px
- Small: 13px

На мобильном hero 40px, section 32px.

## Сетка

Контент max 1280px, поля 24px (mobile) / 40px (desktop).  
Каталог: 2 колонки < 768px, 3 колонки 768–1023, 4 колонки ≥ 1024.  
Карточки без рамок: воздух + фото.

## Радиусы и тени

- `--radius-s: 4px` (кнопки, инпуты)
- `--radius-m: 12px` (карточки, modal)
- Тень только у sticky header после скролла и у modal: `0 12px 40px rgba(24,23,22,.12)`

## Кнопки

1. Primary — заливка accent, белый текст.
2. Ghost — обводка `--line`, текст `--text`.
3. Text — без фона, для ссылок в header.

Не плодить другие типы.

## Карточка товара

Фото 3:4, object-fit cover. Подпись без «бейджей» и иконок корзины. Цена — Manrope 600.

## Формы

Поля на `--surface`, 1px `--line`, focus-ring 2px `--text`. Чекбокс 18px. Ошибка — текст, без красных заливок на всю форму.

## Motion

- Hero load: 700ms opacity + translateY(20px)
- Scroll reveal: 600ms
- Image hover: 350ms scale(1.03)
- Modal: 280ms fade + translate
- `prefers-reduced-motion: reduce` отключает transform-анимации
