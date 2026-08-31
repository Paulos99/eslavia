# Визуальный код AI-фотосессии «Эславия»

## Главное правило

> **Одно AI-фото на товар** — главное изображение карточки (`01.webp`).  
> Остальные кадры — **реальная фотосессия** с taisiy.ru (`02.webp`, `03.webp` …).

AI-кадр продаёт настроение и смысл наряда. Реальные фото показывают точный принт, крой и детали.

---

## ⚠️ Юридическое правило

- Референс продукта с taisiy.ru — **только принт, цвет, крой**
- AI-модель — **оригинальный вымышленный персонаж**, не копия живого человека
- В промпте: `Original fictional model, do NOT replicate likeness of any real person`

---

## Смысл AI-кадра по категориям

| Категория | Смысл | AI-локация | Пример позы |
|-----------|-------|------------|-------------|
| **Пижамы, халаты, сорочки** | Уют дома | Квартира, подоконник, диван | Кофе у окна, golden hour |
| **Платья, сарафаны** | Лёгкость и красота | Улица, терраса, природа | Движение, солнечный свет |
| **Костюмы, толстовки** | Комфорт и стиль | Лофт, город | Candid, editorial |
| **Футболки, топы** | Повседневность | Дом или улица — по модели | Естественная жизнь |
| **Водолазки** | Тепло, layering | Дом у окна или осенняя улица | Уют / прогулка |

AI-кадр всегда **соответствует контексту носки** — пижама не на улице, платье не в спальне.

---

## Визуальный код AI-кадра (editorial, Gorde-inspired)

### Свет
- Golden hour через окно (дом) или на улице (платья)
- Мягкие тени, без студийной вспышки

### Модель
- Вымышленный персонаж, новый для каждой серии
- 30–45 лет, natural beauty, размер 46–60 friendly
- Эталон для пижам: боб dark blonde, подоконник, кружка (МТК-116Л)

### Камера
- Shallow DOF, формат **3:4** (480×600 в карточке)
- Editorial «Casual But Fancy», не каталожная стойка

---

## Workflow на SKU

```bash
python scripts/prepare_ai_photoshoot.py   # скачать реальные фото → 02+, manifest
# сгенерировать ai-{id}.png для каждого SKU (кроме утверждённых)
python scripts/finalize_ai_catalog.py     # 01.webp AI + обновить products.json
```

1. Скачать реальные фото → `02.webp`, `03.webp` …
2. Сгенерировать **один** AI-кадр → `01.webp`
3. Обновить `data/products.json`: `[01 AI, 02 real, 03 real, …]`

Манифест: `data/ai-photoshoot-manifest.json`  
Статус: `data/ai-photoshoot-status.json`

---

## Эталон: Пижама МТК-116Л ✓

| Файл | Источник | Содержание |
|------|----------|------------|
| `01.webp` | **AI** | Подоконник, golden hour, кофе — уют дома |
| `02.webp` | Реальное | Фронт, детали принта |
| `03.webp` | Реальное | Вид сзади, крой |

Путь: `public/images/products/mtk-116l/`

### Промпт-шаблон (пижамы, эталон)

```
Editorial indoor fashion e-commerce, Gorde-inspired "Casual But Fancy".
Original fictional model ONLY — do NOT replicate any real person's likeness.
Woman 34, short dark blonde bob, light olive skin, warm brown eyes, natural makeup.
Navy blue pajama set with orange fox print, hearts, leaves (from product reference only).
Sitting on wide window sill with coffee mug, golden hour through window, monstera nearby.
Cream walls, warm intimate home. INDOORS ONLY. 3:4 vertical photorealistic.
```

---

## Следующие SKU

Тот же промпт-шаблон + свой принт → `01.webp` AI.  
Реальные фото с taisiy.ru → `02+`.
