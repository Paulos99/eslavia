"""Catalog rules shared by the site, PDF, Mini App and Telegram (mirrors post_catalog.py / build_data.py)."""
from __future__ import annotations

import html
import re
import urllib.parse

CATEGORIES = ["Платья", "Сарафаны", "Пижамы для дома", "Сорочки", "Халаты", "Туники"]
CATEGORY_IDS = {"Платья": "platya", "Сарафаны": "sarafany", "Пижамы для дома": "pizhamy",
                "Сорочки": "sorochki", "Халаты": "khalaty", "Туники": "tuniki"}
CATEGORY_TAGS = {"Платья": "#платья", "Сарафаны": "#сарафаны", "Пижамы для дома": "#пижамы",
                 "Пижамы": "#пижамы", "Сорочки": "#сорочки", "Халаты": "#халаты", "Туники": "#туники"}
SIZES = [str(n) for n in range(42, 74, 2)]
ORDER_TG_USERNAME = "baristCoachN"
CHANNEL = "eslavia_opt"
BIG_SIZE_MIN = 58

_TR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
       "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
       "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
       "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}


def product_id(article: str) -> str:
    s = "".join(_TR.get(ch, ch) for ch in (article or "").strip().lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def natural_key(s: str):
    return [(0, int(t), "") if t.isdigit() else (1, 0, t.lower()) for t in re.split(r"(\d+)", s or "") if t != ""]


def category_order(categories_json: list | None) -> list[str]:
    order: list[str] = []
    for c in categories_json or []:
        name = c.get("name") if isinstance(c, dict) else c
        if name and name not in order:
            order.append(name)
    for c in CATEGORIES:
        if c not in order:
            order.append(c)
    return order


def sort_products(products: list[dict], categories_json: list | None) -> list[dict]:
    """Channel / Mini App order: category (categories.json order), then article (natural)."""
    rank = {n: i for i, n in enumerate(category_order(categories_json))}
    return sorted(products, key=lambda p: (rank.get(p.get("category") or "", len(rank)),
                                           natural_key(p.get("category") or ""),
                                           natural_key(p.get("article") or p.get("id"))))


def cap_first(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:]


def display_name(p: dict) -> str:
    raw = p.get("name") or p.get("article") or p["id"]
    raw = re.sub(r"\s*больш(ие|их)\s+размер(ы|ов)\s*", " ", raw, flags=re.I)
    return cap_first(re.sub(r"\s{2,}", " ", raw).strip())


def fmt_price(value) -> str:
    n = int(round(float(value)))
    return f"{n:,}".replace(",", " ")


def category_tag(cat: str) -> str | None:
    tag = CATEGORY_TAGS.get(cat)
    if tag is None and cat:
        word = "".join(ch if ch.isalnum() else "_" for ch in cat.split()[0].lower()).strip("_")
        tag = "#" + word if word else None
    return tag if tag and re.fullmatch(r"#[^\W\d]\w*", tag) else None


def order_message(p: dict, post_url: str | None) -> str:
    link = f"\n{post_url}" if post_url else ""
    return f"Здравствуйте!\nИнтересует модель: {display_name(p)}.{link}\nПодскажите, пожалуйста, условия заказа."


def order_url(p: dict, post_url: str | None) -> str:
    # safe="": "/" must be encoded too, otherwise Telegram Android scrolls to the post instead of opening the DM
    url = f"https://t.me/{ORDER_TG_USERNAME}?text=" + urllib.parse.quote(order_message(p, post_url), safe="")
    assert "t.me/" not in url.split("?", 1)[1]
    return url


def build_caption(p: dict, post_url: str | None) -> str:
    esc = lambda s: html.escape(str(s), quote=False)  # noqa: E731
    sizes = " · ".join(str(s).strip() for s in (p.get("sizes") or []))
    cap = (f"<b>{esc(display_name(p))}</b>\n"
           f"Размеры: {esc(sizes)}\n"
           f"Опт: <b>{fmt_price(p['priceWholesale'])} ₽</b>")
    cap += f"\n\n<a href=\"{html.escape(order_url(p, post_url))}\">Заказать</a>"
    for c in [p.get("category")] + list(p.get("categories") or []):
        t = category_tag(c or "")
        if t:
            cap += "\n\n" + t
            break
    return cap


def size_nums(sizes: list[str]) -> list[int]:
    out: set[int] = set()
    for s in sizes:
        nums = [int(n) for n in re.findall(r"\d+", str(s))]
        if nums:
            out.update(n for n in range(min(nums), max(nums) + 1) if n % 2 == 0)
    return sorted(out)


def recount_categories(categories_json: list, products: list[dict]) -> list:
    out = []
    names = category_order(categories_json)
    existing = {c["name"]: c for c in categories_json if isinstance(c, dict)}
    for name in names:
        items = [p for p in products if name in (p.get("categories") or [p.get("category")])]
        c = dict(existing.get(name) or {"id": CATEGORY_IDS.get(name) or product_id(name), "name": name})
        if name not in existing and not items:
            continue
        c["count"] = len(items)
        cover_ok = any(c.get("image", "").startswith(f"/images/products/{p['id']}/") and c["image"] in (p.get("images") or [])
                       for p in items)
        if items and not cover_ok:
            c["image"] = items[0]["images"][0]
        out.append(c)
    return out
