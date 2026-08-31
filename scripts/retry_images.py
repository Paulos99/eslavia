import json
import socket
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image

socket.setdefaulttimeout(12)

ROOT = Path(".")
products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
dump = json.loads((ROOT / "data/raw/crawl-dump.json").read_text(encoding="utf-8"))
by_name = {x["name"]: x for x in dump["products"]}
UA = "Mozilla/5.0 (compatible; TaisiyaCatalogAudit/1.0)"


def enc(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, quote(p.path, safe="/"), p.query, p.fragment))


def fetch(url: str) -> bytes:
    req = Request(enc(url), headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=20) as r:
            return r.read()
    except Exception as e:
        print(" fail", url, type(e).__name__, e)
        return b""


changed = False
for rec in products:
    if rec["images"]:
        continue
    src = by_name.get(rec["name"], {})
    urls = src.get("imageCacheUrls") or []
    saved = []
    idx = 1
    for url in urls:
        print("get", rec["id"], url, flush=True)
        blob = fetch(url)
        print(rec["id"], url[-50:], len(blob))
        if len(blob) < 800:
            continue
        dest = ROOT / "public" / "images" / "products" / rec["id"] / f"{idx:02d}.webp"
        dest.parent.mkdir(parents=True, exist_ok=True)
        im = Image.open(BytesIO(blob))
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.save(dest, "WEBP", quality=82, method=6)
        saved.append(f"/images/products/{rec['id']}/{idx:02d}.webp")
        idx += 1
    if saved:
        rec["images"] = saved
        changed = True
        print("saved", rec["id"], saved)

if changed:
    (ROOT / "data/products.json").write_text(
        json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cats = json.loads((ROOT / "data/categories.json").read_text(encoding="utf-8"))
    for c in cats:
        items = [x for x in products if x["category"] == c["name"]]
        c["image"] = next((x["images"][0] for x in items if x["images"]), None)
    (ROOT / "data/categories.json").write_text(
        json.dumps(cats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
print("with images", sum(1 for x in products if x["images"]))
