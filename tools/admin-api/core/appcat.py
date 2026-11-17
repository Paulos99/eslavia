"""Mini App data/catalog.json (same structure as eslavia-app/scripts/build_data.py)."""
from __future__ import annotations

import json
import re

from . import catalog as c

CAT_LABEL = {"Пижамы для дома": "Пижамы"}
SIZE_MIN, SIZE_MAX = 42, 72
PHOTOS = 3


def post_url(posts: dict, pid: str) -> str | None:
    mids = (posts.get("posts") or {}).get(pid)
    return f"https://t.me/{posts.get('channel', c.CHANNEL)}/{mids[0]}" if mids else None


def build(products: list[dict], categories_json: list, posts: dict) -> dict:
    items = []
    for p in c.sort_products(products, categories_json):
        imgs = (p.get("images") or [])[:PHOTOS]
        if len(imgs) < PHOTOS:
            continue
        post = post_url(posts, p["id"])
        name = c.display_name(p)
        article = p.get("article") or ""
        title = c.cap_first(re.sub(r"\s{2,}", " ", name.replace(article, "")).strip()) if article else name
        cat = p.get("category") or ""
        nums = c.size_nums(p.get("sizes") or [])
        gallery = [f"./img/{p['id']}/{i:02d}-720.webp" for i in range(1, PHOTOS + 1)]
        items.append({
            "id": p["id"], "article": article, "name": name, "title": title,
            "category": CAT_LABEL.get(cat, cat),
            "sizes": [str(s).strip() for s in p.get("sizes") or []],
            "sizeNums": nums, "big": max(nums or [0]) >= c.BIG_SIZE_MIN,
            "price": int(round(float(p["priceWholesale"]))),
            "material": p.get("material") or None,
            "thumb": f"./img/{p['id']}/01-480.webp", "thumb2x": gallery[0], "images": gallery,
            "post": post or f"https://t.me/{c.CHANNEL}",
            "order": c.order_url(p, post),
        })
    cats = []
    order = c.category_order(categories_json)
    for name in order + sorted({CAT_LABEL.get(p.get("category"), p.get("category")) for p in products} - set(order)):
        label = CAT_LABEL.get(name, name)
        n = sum(1 for it in items if it["category"] == label)
        if n and label not in [x["name"] for x in cats]:
            cats.append({"name": label, "count": n})
    sizes = sorted({n for it in items for n in it["sizeNums"] if SIZE_MIN <= n <= SIZE_MAX})
    return {"brand": "ЭСЛАВИЯ", "channel": f"https://t.me/{c.CHANNEL}", "minOrder": "от 5 000 ₽",
            "count": len(items), "categories": cats, "sizes": sizes, "items": items}


def dumps(catalog: dict) -> bytes:
    return json.dumps(catalog, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
