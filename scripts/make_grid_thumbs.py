# -*- coding: utf-8 -*-
"""Generate lightweight catalog-grid thumbnails.

Originals in public/images/products/** are only READ, never modified.
Output: public/images/thumbs/<product>/<stem>-<width>.webp (plain Lanczos
downscale + WebP q82, no crop, no filters), used by ProductCard/CategoryNav.
Full-size originals stay in use for the lightbox / product modal.

Run after adding or replacing product photos:  python3 scripts/make_grid_thumbs.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SRC_PREFIX = "/images/products/"
DST_PREFIX = "/images/thumbs/"
WIDTHS = (480, 720)
QUALITY = 82


def thumb_rel(src: str, width: int) -> str:
    rest = src[len(SRC_PREFIX):]
    stem, _, ext = rest.rpartition(".")
    return f"{DST_PREFIX}{stem}-{width}.webp"


def make(src: str) -> int:
    if not src.startswith(SRC_PREFIX):
        return 0
    src_file = PUBLIC / src.lstrip("/")
    if not src_file.exists():
        print("missing", src)
        return 0
    n = 0
    im = None
    for w in WIDTHS:
        dst = PUBLIC / thumb_rel(src, w).lstrip("/")
        if dst.exists() and dst.stat().st_mtime >= src_file.stat().st_mtime:
            continue
        if im is None:
            with Image.open(src_file) as raw:
                im = raw.convert("RGB")
        ow, oh = im.size
        out = im if ow <= w else im.resize((w, round(oh * w / ow)), Image.Resampling.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        out.save(dst, "WEBP", quality=QUALITY, method=6)
        n += 1
    return n


def main() -> None:
    products = json.loads((ROOT / "data" / "products.json").read_text("utf-8"))
    categories = json.loads((ROOT / "data" / "categories.json").read_text("utf-8"))
    srcs: list[str] = []
    for p in products:
        srcs += p.get("images", [])[:2]  # cover + hover image in the grid
    srcs += [c["image"] for c in categories if c.get("image")]
    wanted = set()
    n = 0
    for s in dict.fromkeys(srcs):
        n += make(s)
        wanted |= {PUBLIC / thumb_rel(s, w).lstrip("/") for w in WIDTHS} if s.startswith(SRC_PREFIX) else set()
    # drop stale thumbs no longer referenced
    removed = 0
    for f in (PUBLIC / DST_PREFIX.strip("/")).rglob("*.webp"):
        if f not in wanted:
            f.unlink()
            removed += 1
    print(f"wrote {n} thumbs, removed {removed} stale, total {len(wanted)}")


if __name__ == "__main__":
    main()
