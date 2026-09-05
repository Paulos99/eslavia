# -*- coding: utf-8 -*-
"""Convert studio PNGs to WebP, insert as images[1], rebuild card thumbs."""
from __future__ import annotations

import json
from pathlib import Path

import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_catalog_thumbs import make_card

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(r"C:\Users\user\.cursor\projects\c-Users-user-Desktop\assets")
PRODUCTS_PATH = ROOT / "data/products.json"
MANIFEST_PATH = ROOT / "data/ai-photoshoot-manifest.json"
IMG_ROOT = ROOT / "public/images/products"


def png_to_webp(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    im = Image.open(src).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", quality=88, method=6)
    return True


def find_studio_png(pid: str) -> Path | None:
    folder = IMG_ROOT / pid
    for cand in (
        ASSETS / f"studio-{pid}.png",
        folder / f"studio-{pid}.png",
        folder / "studio.png",
        *sorted(ASSETS.glob(f"studio-{pid}*.png")),
        *sorted(folder.glob("studio*.png")),
    ):
        if cand.exists() and cand.suffix.lower() == ".png":
            return cand
    return None


def real_paths(entry: dict, pid: str) -> list[str]:
    reals = list(entry.get("real_images") or [])
    if reals:
        return reals
    folder = IMG_ROOT / pid
    return [f"/images/products/{pid}/{p.name}" for p in sorted(folder.glob("[0-9][0-9].webp")) if p.name != "01.webp"]


def main() -> None:
    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in products}
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_manifest = {e["id"]: e for e in manifest}

    ok, missing = [], []
    for p in products:
        pid = p["id"]
        dest = IMG_ROOT / pid / "studio.webp"
        png = find_studio_png(pid)
        if png and png_to_webp(png, dest):
            print("studio", pid, "from", png.name)
        if not dest.exists():
            missing.append(pid)
            continue
        make_card(dest)
        hero = f"/images/products/{pid}/01.webp"
        studio = f"/images/products/{pid}/studio.webp"
        entry = by_manifest.get(pid, {})
        rest = real_paths(entry, pid)
        rest = [x for x in rest if x not in {hero, studio}]
        by_id[pid]["images"] = [hero, studio] + rest
        ok.append(pid)

    PRODUCTS_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {len(ok)} missing {len(missing)}")
    if missing:
        print("Missing studio:", ", ".join(missing))


if __name__ == "__main__":
    main()
