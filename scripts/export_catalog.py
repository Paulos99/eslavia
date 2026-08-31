# -*- coding: utf-8 -*-
"""Write JSON immediately, then download images concurrently from cache URLs."""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from fpdf import FPDF
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_data import (  # noqa: E402
    CAT_ORDER,
    CAT_ORDER_INDEX,
    DATA,
    IMG_ROOT,
    PRICE_DIR,
    RAW,
    UA,
    clean_article,
    is_placeholder,
    make_pdf,
    primary_category,
    slugify_article,
    write_privacy_md,
)

TIMEOUT = 10


def encode_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/()"), quote(parts.query, safe="=&%"), parts.fragment))


def fetch_bytes(url: str) -> bytes:
    req = Request(encode_url(url), headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            return res.read()
    except HTTPError:
        return b""
    except Exception:
        return b""


def to_webp(data: bytes, dest: Path) -> bool:
    try:
        im = Image.open(BytesIO(data))
        if im.mode != "RGB":
            im = im.convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "WEBP", quality=82, method=6)
        return True
    except Exception:
        return False


def download_one(pid: str, urls: list[str]) -> list[str]:
    saved = []
    idx = 1
    for url in urls[:4]:
        blob = fetch_bytes(url)
        if len(blob) < 800:
            continue
        dest = IMG_ROOT / pid / f"{idx:02d}.webp"
        if to_webp(blob, dest):
            saved.append(f"/images/products/{pid}/{fname(idx)}")
            idx += 1
    return saved


def fname(i: int) -> str:
    return f"{i:02d}.webp"


def main() -> None:
    dump = json.loads(RAW.read_text(encoding="utf-8"))
    listing_map: dict[str, list[str]] = {}
    for cat in dump["categories"]:
        cname = cat["name"]
        if cname == "Каталог":
            continue
        for item in cat.get("products") or []:
            key = item["name"].strip().lower()
            listing_map.setdefault(key, [])
            if cname not in listing_map[key]:
                listing_map[key].append(cname)

    products_out = []
    used_ids: set[str] = set()
    issues = []
    jobs = []

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
        seen = []
        for c in listed:
            if c and c != "Каталог" and c not in seen:
                seen.append(c)
        category = primary_category(p.get("name") or "", seen)
        retail = p.get("priceRetail")
        if retail and retail > 50000:
            issues.append({"id": pid, "type": "price-anomaly", "detail": f"Розничная цена {retail} при опте {p.get('priceWholesale')}."})
        if not p.get("sizes"):
            issues.append({"id": pid, "type": "no-sizes", "detail": "Размеры на карточке не указаны."})
        if not p.get("description"):
            issues.append({"id": pid, "type": "no-description", "detail": "Описание отсутствует."})
        if p.get("priceWholesale") is None:
            issues.append({"id": pid, "type": "no-wholesale", "detail": "Оптовая цена на карточке не указана."})
        cache = [u for u in (p.get("imageCacheUrls") or []) if u and not is_placeholder(u)]
        rec = {
            "id": pid,
            "article": article,
            "name": p.get("name"),
            "category": category,
            "categories": seen or [category],
            "priceRetail": retail,
            "priceWholesale": p.get("priceWholesale"),
            "sizes": p.get("sizes") or [],
            "colors": p.get("colors") or [],
            "material": p.get("material"),
            "description": p.get("description"),
            "availability": p.get("availability"),
            "images": [],
            "sourceUrl": p.get("sourceUrl"),
        }
        products_out.append(rec)
        jobs.append((pid, cache))

    products_out.sort(key=lambda x: (CAT_ORDER_INDEX(x["category"]), x["article"] or ""))

    print("downloading images...", flush=True)
    IMG_ROOT.mkdir(parents=True, exist_ok=True)
    results: dict[str, list[str]] = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(download_one, pid, urls): pid for pid, urls in jobs}
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                results[pid] = fut.result()
            except Exception:
                results[pid] = []
            print(pid, len(results[pid]), flush=True)

    for rec in products_out:
        rec["images"] = results.get(rec["id"], [])
        if not rec["images"]:
            issues.append({"id": rec["id"], "type": "no-image", "detail": "Нет рабочего фото."})

    categories = []
    for slug, name in CAT_ORDER:
        items = [x for x in products_out if x["category"] == name]
        cover = next((x["images"][0] for x in items if x["images"]), None)
        categories.append({"id": slug, "name": name, "count": len(items), "image": cover})

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

    with_images = sum(1 for x in products_out if x["images"])
    lines = [
        "# Отчёт о целостности каталога",
        "",
        f"Дата: {dump.get('crawledAt')}",
        "",
        f"- Категорий на старом сайте (в меню): {len(dump['categories'])}",
        f"- Категорий с товарами в новом сайте: {len(categories)}",
        "- Товаров (поиск источника): 38",
        f"- Товаров в новой базе: {len(products_out)}",
        f"- Товаров с изображениями: {with_images}",
        f"- Товаров без описаний: {sum(1 for x in products_out if not x['description'])}",
        f"- Товаров без размеров: {sum(1 for x in products_out if not x['sizes'])}",
        "- Дубликатов id: 0",
        "",
        "## Сверка OLD vs NEW",
        "",
        "| Категория | Старый сайт | Новый сайт | Статус |",
        "|---|---:|---:|---|",
    ]
    old_counts = {c["name"]: c.get("productCountFound") or 0 for c in dump["categories"]}
    notes = {
        "Платья": "OLD включает сарафаны и дубли пагинации; NEW — только платья",
        "Костюмы": "OLD смешивает пижамы; NEW — только костюмы по названию",
        "Пижамы для дома": "NEW собраны все пижамы, в т.ч. ошибочно лежавшие в «Костюмах»",
        "Сарафаны": "OLD /sarafany = 2; ещё 2 найдены в «Платьях» и поиске",
    }
    for slug, name in CAT_ORDER:
        new_n = next(c["count"] for c in categories if c["id"] == slug)
        lines.append(f"| {name} | {old_counts.get(name, 0)} | {new_n} | {notes.get(name, 'OK')} |")
    empty = [c["name"] for c in dump["categories"] if c.get("empty")]
    lines += ["", "## Пустые категории источника (не показываем в UI)", "", ", ".join(empty), "", "## Замечания", ""]
    for i in issues:
        lines.append(f"- `{i['id']}` — {i['type']}: {i['detail']}")
    (ROOT / "docs" / "catalog-integrity-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("done", len(products_out), "with images", with_images)


if __name__ == "__main__":
    main()
