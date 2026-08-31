# -*- coding: utf-8 -*-
"""Finalize catalog: 01 AI + 02+ real for every SKU. Retry missing AI from manifest."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(r"C:\Users\user\.cursor\projects\c-Users-user-Desktop\assets")
PRODUCTS = ROOT / "data/products.json"
MANIFEST = ROOT / "data/ai-photoshoot-manifest.json"
SKIP = {"mtk-116l"}


def png_to_webp(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    im = Image.open(src).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", quality=88, method=6)
    return True


def main() -> None:
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in products}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    ok, missing = [], []
    for entry in manifest:
        pid = entry["id"]
        reals = entry.get("real_images") or []
        ai_webp = Path(entry["ai_output"])

        if pid in SKIP:
            hero = ROOT / "public/images/products/mtk-116l/01.webp"
            if hero.exists():
                by_id[pid]["images"] = [f"/images/products/{pid}/01.webp"] + reals[:2]
                ok.append(pid)
            continue

        png = ASSETS / f"ai-{pid}.png"
        if png_to_webp(png, ai_webp):
            by_id[pid]["images"] = [f"/images/products/{pid}/01.webp"] + reals
            ok.append(pid)
        else:
            missing.append(pid)

    PRODUCTS.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

    cats = ROOT / "data/categories.json"
    if cats.exists():
        data = json.loads(cats.read_text(encoding="utf-8"))
        for c in data:
            items = [p for p in products if p["category"] == c["name"]]
            c["image"] = next((p["images"][0] for p in items if p.get("images")), None)
        cats.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    report = ROOT / "data/ai-photoshoot-status.json"
    report.write_text(
        json.dumps({"ok": ok, "missing": missing, "total": len(manifest) + 1}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OK: {len(ok)}/{len(manifest)+1}")
    if missing:
        print("Missing AI:", ", ".join(missing))


if __name__ == "__main__":
    main()
