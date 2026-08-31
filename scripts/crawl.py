# -*- coding: utf-8 -*-
"""Phase 1: crawl taisiy.ru (OpenCart) into data/raw/."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE = "https://taisiy.ru"
UA = "Mozilla/5.0 (compatible; TaisiyaCatalogAudit/1.0)"

CATEGORY_URLS = [
    {"slug": "katalog", "url": f"{BASE}/katalog", "name": "Каталог"},
    {"slug": "kostyumy", "url": f"{BASE}/katalog/kostyumy", "name": "Костюмы"},
    {"slug": "pizhamy", "url": f"{BASE}/katalog/pizhamy", "name": "Пижамы для дома"},
    {"slug": "platjya", "url": f"{BASE}/katalog/platjya", "name": "Платья"},
    {"slug": "sarafany", "url": f"{BASE}/katalog/sarafany", "name": "Сарафаны"},
    {"slug": "tolstovki", "url": f"{BASE}/katalog/tolstovki", "name": "Толстовки"},
    {"slug": "tuniki", "url": f"{BASE}/katalog/tuniki", "name": "Туники"},
    {"slug": "vodolazki", "url": f"{BASE}/vodolazki", "name": "Водолазки"},
    {"slug": "sorochki", "url": f"{BASE}/sorochki", "name": "Сорочки"},
    {"slug": "futbolki", "url": f"{BASE}/futbolki", "name": "Футболки"},
    {"slug": "khalaty", "url": f"{BASE}/khalaty", "name": "Халаты"},
    {"slug": "velosipedki", "url": f"{BASE}/velosipedki", "name": "Велосипедки"},
    {"slug": "topy", "url": f"{BASE}/topy", "name": "Топы"},
]

INFO_PAGES = [
    {"id": "home", "url": f"{BASE}/"},
    {"id": "about", "url": f"{BASE}/about_us"},
    {"id": "delivery", "url": f"{BASE}/delivery"},
    {"id": "privacy", "url": f"{BASE}/privacy"},
    {"id": "size-guide", "url": f"{BASE}/tablica-razmerov"},
    {"id": "contact", "url": f"{BASE}/contact"},
    {"id": "sitemap", "url": f"{BASE}/sitemap"},
    {"id": "return", "url": f"{BASE}/return-add"},
    {"id": "search", "url": f"{BASE}/index.php?route=product/search&search=&limit=100"},
]


def encode_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/")
    query = urllib.parse.quote(parts.query, safe="=&%")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def fetch_text(url: str, retries: int = 4) -> tuple[int, str, str]:
    req = urllib.request.Request(
        encode_url(url), headers={"User-Agent": UA, "Accept": "text/html"}
    )
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=40) as res:
                html = res.read().decode("utf-8", errors="replace")
                return res.status, res.geturl(), html
        except urllib.error.HTTPError as e:
            html = e.read().decode("utf-8", errors="replace") if e.fp else ""
            return e.code, url, html
        except Exception as e:
            last_err = e
            time.sleep(1.2 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def product_key(url: str) -> str:
    path = urllib.parse.urlsplit(url).path.rstrip("/")
    slug = path.split("/")[-1]
    return urllib.parse.unquote(slug).lower()


def decode_html(s: str) -> str:
    s = unescape(s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_tags(html: str) -> str:
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return decode_html(html).replace(" \n", "\n")


def unique(items: list) -> list:
    out = []
    seen = set()
    for x in items:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def cache_to_original(url: str | None) -> str | None:
    if not url:
        return None
    u = url.split("?")[0]
    u = u.replace("/image/cache/", "/image/")
    u = re.sub(r"-(\d+)x(\d+)(\.(jpe?g|png|webp|gif))$", r"\3", u, flags=re.I)
    return u


def extract_product_links(html: str) -> list[dict]:
    links = []
    for m in re.finditer(
        r'<div class="product-thumb">[\s\S]*?<h4><a href="([^"]+)">([\s\S]*?)</a></h4>',
        html,
    ):
        href = unescape(m.group(1)).split("?")[0]
        links.append({"url": href, "name": decode_html(m.group(2))})
    return links


def extract_pagination_pages(html: str, base_url: str) -> tuple[list[str], int | None]:
    pages = {base_url}
    for m in re.finditer(r'href="(https://taisiy\.ru/[^"]*(?:[?&]page=\d+)[^"]*)"', html):
        pages.add(unescape(m.group(1)))
    shown = re.search(r"Показано с \d+ по \d+ из (\d+)", html)
    total = int(shown.group(1)) if shown else None
    return list(pages), total


def extract_material(description: str | None) -> str | None:
    if not description:
        return None
    patterns = [
        r"ткань\s+100%\s*хлопок",
        r"из\s+100%\s*хлопка",
        r"100%\s*хлопок",
        r"из\s+натурального\s+хлопка",
        r"из\s+кулирки",
    ]
    for p in patterns:
        m = re.search(p, description, flags=re.I)
        if m:
            t = m.group(0).lower()
            if "кулирк" in t:
                return "кулирка"
            if "хлоп" in t:
                return "100% хлопок"
            return m.group(0)
    return None


def parse_product(html: str, url: str) -> dict:
    name_m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html)
    name = decode_html(name_m.group(1)) if name_m else None

    article_m = re.search(r"<li><b>Модель:</b>\s*([^<]+)</li>", html)
    article = decode_html(article_m.group(1)) if article_m else None

    avail_m = re.search(r"<li><b>Наличие:</b>\s*([^<]+)</li>", html)
    availability = decode_html(avail_m.group(1)) if avail_m else None

    id_m = re.search(r"wishlist\.add\('(\d+)'\)", html)
    oc_id = id_m.group(1) if id_m else None

    retail_m = re.search(r'data-price="([\d.]+)"\s+class="calc-price"', html)
    price_retail = float(retail_m.group(1)) if retail_m else None

    wholesale_m = re.search(r'<span class="opt-chena">([^<]+)</span>', html)
    price_wholesale = None
    if wholesale_m:
        n = re.sub(r"[^\d.,]", "", wholesale_m.group(1)).replace(",", ".")
        price_wholesale = float(n) if n else None

    sizes = []
    size_block = re.search(
        r'<label class="control-label">Размер</label>([\s\S]*?)</div>\s*</div>', html
    )
    if size_block:
        for sm in re.finditer(r'<label for="\d+">\s*([^<]+?)\s*</label>', size_block.group(1)):
            s = decode_html(sm.group(1))
            if s:
                sizes.append(s)

    desc_m = re.search(r'id="tab-description">([\s\S]*?)</div>', html)
    description = strip_tags(desc_m.group(1)) if desc_m else None
    if description:
        description = re.sub(r"\n+", "\n", description).strip() or None

    image_urls = re.findall(r'<a class="thumbnail" href="(https://taisiy\.ru/image/cache/[^"]+)"', html)

    return {
        "sourceUrl": url,
        "ocId": oc_id,
        "name": name,
        "article": article,
        "availability": availability,
        "priceRetail": price_retail,
        "priceWholesale": price_wholesale,
        "sizes": unique(sizes),
        "colors": [],
        "material": extract_material(description),
        "description": description,
        "imageCacheUrls": unique(image_urls),
        "imageOriginalCandidates": unique([cache_to_original(u) for u in image_urls]),
    }


def parse_size_table(html: str) -> list[list[str]]:
    rows = []
    table = re.search(r"<table[\s\S]*?</table>", html, flags=re.I)
    if not table:
        return rows
    for tr in re.findall(r"<tr[\s\S]*?</tr>", table.group(0), flags=re.I):
        cells = [
            decode_html(re.sub(r"<[^>]+>", " ", c))
            for c in re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", tr, flags=re.I)
        ]
        if cells:
            rows.append(cells)
    return rows


def extract_h1_content(html: str) -> str:
    m = re.search(
        r'<div id="content"[^>]*>[\s\S]*?<h1[^>]*>[\s\S]*?</h1>([\s\S]*?)</div>\s*<footer',
        html,
        flags=re.I,
    )
    if not m:
        m = re.search(r"<h1[^>]*>[\s\S]*?</h1>([\s\S]*?)<footer", html, flags=re.I)
    return strip_tags(m.group(1)) if m else ""


def slug_from_url(url: str, i: int) -> str:
    slug = url.replace(BASE + "/", "")
    slug = re.sub(r"[^\w\-]+", "_", slug, flags=re.U)
    return slug or f"p{i}"


def crawl_category(cat: dict) -> dict:
    status, final_url, html = fetch_text(cat["url"])
    (RAW / "categories").mkdir(parents=True, exist_ok=True)
    (RAW / "categories" / f"{cat['slug']}.html").write_text(html, encoding="utf-8")

    not_found = status >= 400 or bool(re.search(r"не найдена", html, flags=re.I))
    empty = bool(re.search(r"нет товаров", html, flags=re.I))
    if not_found or empty:
        return {
            **cat,
            "status": status,
            "empty": True,
            "productCountListed": 0,
            "productCountFound": 0,
            "products": [],
            "pagesFetched": 1,
        }

    pages, total = extract_pagination_pages(html, cat["url"])
    extra = [p for p in pages if p != cat["url"] and re.search(r"[?&]page=\d+", p)]
    extra.sort(key=lambda p: int(re.search(r"[?&]page=(\d+)", p).group(1)))
    all_html = html
    for p in extra:
        time.sleep(0.25)
        _, _, next_html = fetch_text(p)
        page_num = re.search(r"[?&]page=(\d+)", p).group(1)
        (RAW / "categories" / f"{cat['slug']}-p{page_num}.html").write_text(next_html, encoding="utf-8")
        all_html += "\n" + next_html

    products = extract_product_links(all_html)
    seen = set()
    uniq = []
    for p in products:
        if p["url"] in seen:
            continue
        seen.add(p["url"])
        uniq.append(p)

    return {
        **cat,
        "status": status,
        "empty": len(uniq) == 0,
        "productCountListed": total,
        "productCountFound": len(uniq),
        "products": uniq,
        "pagesFetched": 1 + len(extra),
    }


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "products").mkdir(parents=True, exist_ok=True)
    (RAW / "pages").mkdir(parents=True, exist_ok=True)
    (RAW / "categories").mkdir(parents=True, exist_ok=True)

    pages = {}
    for p in INFO_PAGES:
        print("page", p["id"], p["url"], flush=True)
        status, final_url, html = fetch_text(p["url"])
        (RAW / "pages" / f"{p['id']}.html").write_text(html, encoding="utf-8")
        pages[p["id"]] = {
            "url": p["url"],
            "status": status,
            "finalUrl": final_url,
            "bytes": len(html.encode("utf-8")),
        }
        time.sleep(0.2)

    categories = []
    product_index: dict[str, dict] = {}

    def add_product(url: str, name: str, category: str | None) -> None:
        key = product_key(url)
        if not key:
            return
        if key not in product_index:
            product_index[key] = {
                "url": url.split("?")[0],
                "name": name,
                "categories": [category] if category else [],
            }
            return
        rec = product_index[key]
        if category and category not in rec["categories"]:
            rec["categories"].append(category)
        # Prefer a shorter canonical URL when available
        if len(url.split("?")[0]) < len(rec["url"]):
            rec["url"] = url.split("?")[0]

    for cat in CATEGORY_URLS:
        print("category", cat["slug"], flush=True)
        crawled = crawl_category(cat)
        categories.append(crawled)
        for p in crawled.get("products") or []:
            add_product(p["url"], p["name"], crawled["name"])
        time.sleep(0.25)

    search_html = (RAW / "pages" / "search.html").read_text(encoding="utf-8")
    for p in extract_product_links(search_html):
        add_product(p["url"], p["name"], None)

    products = []
    for i, rec in enumerate(product_index.values(), start=1):
        print(f"product {i}/{len(product_index)} {rec['url']}", flush=True)
        slug = slug_from_url(rec["url"], i)
        html_path = RAW / "products" / f"{slug}.html"
        if html_path.exists() and html_path.stat().st_size > 1000:
            html = html_path.read_text(encoding="utf-8")
            status = 200
        else:
            status, _, html = fetch_text(rec["url"])
            html_path.write_text(html, encoding="utf-8")
        parsed = parse_product(html, rec["url"])
        parsed["httpStatus"] = status
        parsed["listedName"] = rec["name"]
        parsed["listedCategories"] = [c for c in rec["categories"] if c != "Каталог"]
        products.append(parsed)
        time.sleep(0.2)

    dump = {
        "crawledAt": datetime.now(timezone.utc).isoformat(),
        "source": BASE,
        "pages": pages,
        "categories": [
            {
                "slug": c["slug"],
                "name": c["name"],
                "url": c["url"],
                "status": c["status"],
                "empty": c["empty"],
                "productCountListed": c.get("productCountListed"),
                "productCountFound": c.get("productCountFound"),
                "pagesFetched": c.get("pagesFetched"),
                "products": c.get("products"),
            }
            for c in categories
        ],
        "products": products,
        "sizeTable": parse_size_table((RAW / "pages" / "size-guide.html").read_text(encoding="utf-8")),
        "aboutText": extract_h1_content((RAW / "pages" / "about.html").read_text(encoding="utf-8")),
        "deliveryText": extract_h1_content((RAW / "pages" / "delivery.html").read_text(encoding="utf-8")),
        "privacyText": extract_h1_content((RAW / "pages" / "privacy.html").read_text(encoding="utf-8")),
        "contactText": extract_h1_content((RAW / "pages" / "contact.html").read_text(encoding="utf-8")),
    }
    (RAW / "crawl-dump.json").write_text(
        json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE products:", len(products), "categories:", len(categories), flush=True)


if __name__ == "__main__":
    main()
