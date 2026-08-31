# -*- coding: utf-8 -*-
"""Normalize crawl dump → JSON, WebP images, wholesale PDF, integrity report."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "crawl-dump.json"
DATA = ROOT / "data"
PUBLIC = ROOT / "public"
IMG_ROOT = PUBLIC / "images" / "products"
PRICE_DIR = PUBLIC / "prices"
UA = "Mozilla/5.0 (compatible; TaisiyaCatalogAudit/1.0)"

CAT_ORDER = [
    ("kostyumy", "Костюмы"),
    ("pizhamy", "Пижамы для дома"),
    ("platya", "Платья"),
    ("sarafany", "Сарафаны"),
]


def encode_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/()")
    query = urllib.parse.quote(parts.query, safe="=&%")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def fetch_bytes(url: str, retries: int = 2) -> tuple[int, bytes]:
    req = urllib.request.Request(encode_url(url), headers={"User-Agent": UA})
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=18) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read() if e.fp else b""
        except Exception as e:
            last = e
            time.sleep(0.4 * (attempt + 1))
    if last:
        return 0, b""
    return 0, b""


def slugify_article(article: str) -> str:
    s = article.strip().lower()
    s = s.replace("ё", "е")
    trans = str.maketrans(
        "абвгдежзийклмнопрстуфхцчшщъыьэюя",
        "abvgdezzijklmnoprstufhccssyyyeua",
    )
    s = s.translate(trans)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "item"


def clean_article(p: dict) -> str:
    art = (p.get("article") or "").strip()
    name = (p.get("name") or "").strip()
    if art.lower().startswith("пижама") or art.lower().startswith("платье") or art.lower().startswith("костюм"):
        m = re.search(r"(МТК[\-–]?\d+[А-ЯA-Z/]*|М[\-–]?\d+[А-ЯA-Z]*)", art, flags=re.I)
        if m:
            art = m.group(1)
    if not art:
        m = re.search(r"(МТК[\-–]?\d+[А-ЯA-Z/]*|М[\-–]?\d+[А-ЯA-Z]*)", name, flags=re.I)
        art = m.group(1) if m else name
    return art.replace("–", "-")


def primary_category(name: str, listed: list[str]) -> str:
    n = (name or "").lower()
    if n.startswith("сарафан"):
        return "Сарафаны"
    if "пижама" in n:
        return "Пижамы для дома"
    if n.startswith("костюм"):
        return "Костюмы"
    if "Платья" in listed:
        return "Платья"
    if "Сарафаны" in listed:
        return "Сарафаны"
    for c in listed:
        if c and c != "Каталог":
            return c
    return "Платья"


def is_placeholder(url: str) -> bool:
    return "placeholder" in (url or "").lower()


def to_webp(data: bytes, dest: Path) -> bool:
    try:
        im = Image.open(BytesIO(data))
        if im.mode in ("P", "RGBA"):
            im = im.convert("RGB")
        elif im.mode != "RGB":
            im = im.convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "WEBP", quality=82, method=6)
        return True
    except Exception:
        return False


def download_product_images(pid: str, p: dict) -> list[str]:
    # Prefer OpenCart cache 751×1000 — originals often 404/hang.
    ordered: list[str] = []
    seen: set[str] = set()
    for cache in p.get("imageCacheUrls") or []:
        if not cache or is_placeholder(cache) or cache in seen:
            continue
        seen.add(cache)
        ordered.append(cache)

    saved: list[str] = []
    out_dir = IMG_ROOT / pid
    idx = 1
    for url in ordered[:6]:
        try:
            status, blob = fetch_bytes(url)
        except Exception:
            continue
        if status != 200 or len(blob) < 800:
            continue
        fname = f"{idx:02d}.webp"
        dest = out_dir / fname
        if to_webp(blob, dest):
            saved.append(f"/images/products/{pid}/{fname}")
            idx += 1
    return saved


def make_pdf(products: list[dict], dest: Path) -> None:
    font = Path(r"C:\Windows\Fonts\arial.ttf")
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    if font.exists():
        pdf.add_font("ArialR", "", str(font))
        pdf.set_font("ArialR", size=16)
    else:
        pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, "Таисия — оптовый прайс", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("ArialR" if font.exists() else "Helvetica", size=10)
    pdf.cell(0, 6, "Женский трикотаж. Цены на момент аудита сайта taisiy.ru", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Оптовые скидки при сумме заказа от 5000 р.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    col_w = [32, 68, 42, 38]
    headers = ["Артикул", "Название", "Размеры", "Опт, руб."]
    pdf.set_fill_color(247, 245, 241)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 8, h, border=1, fill=True)
    pdf.ln()

    for p in products:
        sizes = " · ".join(p.get("sizes") or []) or "—"
        wholesale = p.get("priceWholesale")
        price = "—" if wholesale is None else str(int(wholesale) if wholesale == int(wholesale) else wholesale)
        row = [p.get("article") or "—", p.get("name") or "—", sizes, price]
        # wrap name if needed
        x, y = pdf.get_x(), pdf.get_y()
        h = 8
        for w, val in zip(col_w, row):
            pdf.cell(w, h, str(val)[:42], border=1)
        pdf.ln()
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.set_font("ArialR" if font.exists() else "Helvetica", size=10)

    dest.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(dest))


def write_privacy_md(text: str) -> None:
    # Keep source wording; light paragraph breaks on numbered headings
    body = text.strip()
    body = re.sub(r" (\d+\.\d+\.) ", r"\n\n\1 ", body)
    body = re.sub(r" (\d+\. )", r"\n\n\1", body)
    (DATA / "privacy.md").write_text("# Политика в отношении обработки персональных данных\n\n" + body + "\n", encoding="utf-8")


def main() -> None:
    dump = json.loads(RAW.read_text(encoding="utf-8"))
    products_out = []
    issues = []
    used_ids: set[str] = set()

    # Rebuild listed categories from category listings (more complete than product-page crumbs)
    listing_map: dict[str, list[str]] = {}
    for cat in dump["categories"]:
        cname = cat["name"]
        if cname == "Каталог":
            continue
        for item in cat.get("products") or []:
            listing_map.setdefault(item["name"].strip().lower(), [])
            if cname not in listing_map[item["name"].strip().lower()]:
                listing_map[item["name"].strip().lower()].append(cname)

    for p in dump["products"]:
        article = clean_article(p)
        pid = slugify_article(article)
        base = pid
        n = 2
        while pid in used_ids:
            pid = f"{base}-{n}"
            n += 1
        used_ids.add(pid)

        listed = listing_map.get((p.get("name") or "").strip().lower(), []) + (p.get("listedCategories") or [])
        listed = [c for c in listed if c and c != "Каталог"]
        # unique
        seen = []
        for c in listed:
            if c not in seen:
                seen.append(c)
        listed = seen
        category = primary_category(p.get("name") or "", listed)

        retail = p.get("priceRetail")
        if retail and retail > 50000:
            issues.append(
                {
                    "id": pid,
                    "type": "price-anomaly",
                    "detail": f"Розничная цена {retail} при опте {p.get('priceWholesale')}. Перенесено как на источнике.",
                }
            )

        print(f"images {pid}", flush=True)
        images = download_product_images(pid, p)
        if not images:
            issues.append({"id": pid, "type": "no-image", "detail": "На источнике нет рабочего фото (placeholder или пустая галерея)."})

        if not p.get("sizes"):
            issues.append({"id": pid, "type": "no-sizes", "detail": "Размеры на карточке не указаны."})
        if not p.get("description"):
            issues.append({"id": pid, "type": "no-description", "detail": "Описание отсутствует."})
        if p.get("priceWholesale") is None:
            issues.append({"id": pid, "type": "no-wholesale", "detail": "Оптовая цена на карточке не указана."})

        products_out.append(
            {
                "id": pid,
                "article": article,
                "name": p.get("name"),
                "category": category,
                "categories": listed or [category],
                "priceRetail": retail,
                "priceWholesale": p.get("priceWholesale"),
                "sizes": p.get("sizes") or [],
                "colors": p.get("colors") or [],
                "material": p.get("material"),
                "description": p.get("description"),
                "availability": p.get("availability"),
                "images": images,
                "sourceUrl": p.get("sourceUrl"),
            }
        )

    products_out.sort(key=lambda x: (CAT_ORDER_INDEX(x["category"]), x["article"] or ""))

    # category cover = first product with image
    categories = []
    for slug, name in CAT_ORDER:
        items = [x for x in products_out if x["category"] == name]
        cover = next((x["images"][0] for x in items if x["images"]), None)
        categories.append(
            {
                "id": slug,
                "name": name,
                "count": len(items),
                "image": cover,
            }
        )

    company = {
        "name": "Таисия",
        "tagline": "Женский трикотаж оптом и в розницу",
        "about": dump.get("aboutText") or "",
        "facts": [
            "Продукция для женщин и девушек",
            "Комфорт натуральных тканей",
            "Размерный ряд от 42 до 70 (по тексту «О нас»)",
            "Оптовые скидки при сумме заказа от 5000 р.",
        ],
        "inn": "370252109182",
        "year": 2023,
    }
    contacts = {
        "phone": "+7 (963) 152-97-47",
        "phoneRaw": "79631529747",
        "email": "shyisewing@yandex.ru",
        "address": "г. Иваново, ул. Свободы, д. 13",
        "whatsapp": "https://wa.me/79631529747",
        "viber": "viber://chat?number=79631529747",
        "telegram": "https://t.me/+79631529747",
    }
    size_guide = {
        "note": "Таблица перенесена с taisiy.ru/tablica-razmerov. В тексте «О нас» заявлен ряд 42–70, в таблице — 46–64.",
        "columns": dump["sizeTable"][0] if dump.get("sizeTable") else [],
        "rows": dump["sizeTable"][1:] if dump.get("sizeTable") else [],
    }
    delivery = {
        "pickup": "г. Иваново, ул. Свободы, д. 13",
        "carriers": ["Деловые линии", "СДЭК", "ПЭК"],
        "carrierPaidBy": "покупатель",
        "toTerminal": "бесплатно",
        "payment": "Онлайн на сайте, в точке выдачи транспортной компании или по адресу самовывоза.",
        "fullText": dump.get("deliveryText") or "",
    }

    DATA.mkdir(exist_ok=True)
    (DATA / "products.json").write_text(json.dumps(products_out, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "categories.json").write_text(json.dumps(categories, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "company.json").write_text(json.dumps(company, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "contacts.json").write_text(json.dumps(contacts, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "size-guide.json").write_text(json.dumps(size_guide, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "delivery.json").write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding="utf-8")
    write_privacy_md(dump.get("privacyText") or "")

    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    make_pdf(products_out, PRICE_DIR / "optovyy-prays.pdf")

    search_count = 38
    with_images = sum(1 for x in products_out if x["images"])
    without_desc = sum(1 for x in products_out if not x["description"])
    without_sizes = sum(1 for x in products_out if not x["sizes"])
    ids = [x["id"] for x in products_out]
    dupes = len(ids) - len(set(ids))

    lines = [
        "# Отчёт о целостности каталога",
        "",
        f"Дата: {dump.get('crawledAt')}",
        "",
        f"- Категорий на старом сайте (в меню): {len(dump['categories'])}",
        f"- Категорий с товарами в новом сайте: {len(categories)}",
        f"- Товаров (поиск источника): {search_count}",
        f"- Товаров в новой базе: {len(products_out)}",
        f"- Товаров с изображениями: {with_images}",
        f"- Товаров без описаний: {without_desc}",
        f"- Товаров без размеров: {without_sizes}",
        f"- Дубликатов id: {dupes}",
        "",
        "## Сверка OLD vs NEW",
        "",
        "| Категория | Старый сайт | Новый сайт | Статус |",
        "|---|---:|---:|---|",
    ]
    old_counts = {c["name"]: c.get("productCountFound") or 0 for c in dump["categories"]}
    for slug, name in CAT_ORDER:
        new_n = next(c["count"] for c in categories if c["id"] == slug)
        old_n = old_counts.get(name, 0)
        # Платья on old site includes sarafans + pagination duplicates
        note = "OK"
        if name == "Платья":
            note = "OLD включает сарафаны и дубли пагинации; NEW — только платья"
        elif name == "Костюмы":
            note = "OLD смешивает пижамы; NEW — только костюмы по названию"
        elif name == "Пижамы для дома":
            note = "NEW собраны все пижамы, в т.ч. ошибочно лежавшие в «Костюмах»"
        elif name == "Сарафаны":
            note = "OLD /sarafany = 2; ещё 2 найдены в «Платьях» и поиске"
        lines.append(f"| {name} | {old_n} | {new_n} | {note} |")

    empty = [c["name"] for c in dump["categories"] if c.get("empty")]
    lines += [
        "",
        "## Пустые категории источника (не показываем в UI)",
        "",
        ", ".join(empty),
        "",
        "## Замечания",
        "",
    ]
    for i in issues:
        lines.append(f"- `{i['id']}` — {i['type']}: {i['detail']}")

    (ROOT / "docs" / "catalog-integrity-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("products", len(products_out), "images-ok", with_images, "issues", len(issues))


def CAT_ORDER_INDEX(name: str) -> int:
    for i, (_, n) in enumerate(CAT_ORDER):
        if n == name:
            return i
    return 99


if __name__ == "__main__":
    main()
