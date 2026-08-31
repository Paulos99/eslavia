# -*- coding: utf-8 -*-
"""Apply generated AI PNGs from assets/ to product 01.webp and update products.json."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(r"C:\Users\user\.cursor\projects\c-Users-user-Desktop\assets")
PRODUCTS_PATH = ROOT / "data/products.json"
MANIFEST_PATH = ROOT / "data/ai-photoshoot-manifest.json"
SKIP = {"mtk-116l"}


def png_to_webp(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    im = Image.open(src).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", quality=88, method=6)
    return True


def main() -> None:
    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in products}
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    ok = 0
    missing = []
    for entry in manifest:
        pid = entry["id"]
        if pid in SKIP:
            ai = Path(entry.get("ai_output", ""))
            if ai.exists() or (ROOT / "public" / "images" / "products" / pid / "01.webp").exists():
                by_id[pid]["images"] = [f"/images/products/{pid}/01.webp"] + entry["real_images"]
                ok += 1
            continue

        png = ASSETS / f"ai-{pid}.png"
        dest = Path(entry["ai_output"])
        if png_to_webp(png, dest):
            by_id[pid]["images"] = [f"/images/products/{pid}/01.webp"] + entry["real_images"]
            ok += 1
            print("OK", pid)
        else:
            missing.append(pid)
            print("MISSING", pid)

    PRODUCTS_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

    cats_path = ROOT / "data/categories.json"
    if cats_path.exists():
        cats = json.loads(cats_path.read_text(encoding="utf-8"))
        for c in cats:
            items = [x for x in products if x["category"] == c["name"]]
            c["image"] = next((x["images"][0] for x in items if x.get("images")), None)
        cats_path.write_text(json.dumps(cats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nApplied {ok}/{len(manifest)+1} (incl skip)")
    if missing:
        print("Still missing:", ", ".join(missing))


if __name__ == "__main__":
    main()
