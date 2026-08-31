# -*- coding: utf-8 -*-
"""Remove visually duplicate product photos and reindex remaining files."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
IMG_ROOT = PUBLIC / "images" / "products"
PRODUCTS = ROOT / "data" / "products.json"
CATEGORIES = ROOT / "data" / "categories.json"
HAMMING_LIMIT = 2
HASH_SIZE = 12


def ahash(path: Path, size: int = HASH_SIZE) -> int:
    im = Image.open(path).convert("L").resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(im.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for p in pixels:
        bits = (bits << 1) | (1 if p >= avg else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def local_path(rel: str) -> Path:
    return PUBLIC / rel.lstrip("/")


def unique_keep(paths: list[Path]) -> list[Path]:
    keep: list[tuple[Path, int, str]] = []
    for path in paths:
        if not path.exists():
            continue
        digest = md5(path)
        ah = ahash(path)
        dup = False
        for _, kah, kmd in keep:
            if digest == kmd or hamming(ah, kah) <= HAMMING_LIMIT:
                dup = True
                break
        if not dup:
            keep.append((path, ah, digest))
    return [p for p, _, _ in keep]


def reindex(pid: str, keep: list[Path]) -> list[str]:
    folder = IMG_ROOT / pid
    tmp = folder / "_unique"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for i, src in enumerate(keep, start=1):
        dest = tmp / f"{i:02d}.webp"
        shutil.copy2(src, dest)
        saved.append(f"/images/products/{pid}/{i:02d}.webp")
    for f in folder.glob("*.webp"):
        f.unlink()
    for f in tmp.glob("*.webp"):
        f.rename(folder / f.name)
    tmp.rmdir()
    leftover = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() != ".webp"]
    for p in leftover:
        p.unlink()
    return saved


def main() -> None:
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    report = []
    for rec in products:
        pid = rec["id"]
        rels = rec.get("images") or []
        files = [local_path(r) for r in rels]
        existing = [p for p in files if p.exists()]
        keep = unique_keep(existing)
        if not existing:
            rec["images"] = []
            continue
        if len(keep) == len(existing) and all(a.name == b.name for a, b in zip(keep, existing)):
            continue
        before = len(existing)
        rec["images"] = reindex(pid, keep)
        report.append(
            {
                "id": pid,
                "article": rec.get("article"),
                "before": before,
                "after": len(rec["images"]),
                "removed": before - len(rec["images"]),
            }
        )

    PRODUCTS.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    categories = json.loads(CATEGORIES.read_text(encoding="utf-8"))
    by_cat: dict[str, list] = {}
    for rec in products:
        by_cat.setdefault(rec["category"], []).append(rec)
    for cat in categories:
        items = by_cat.get(cat["name"], [])
        cover = next((x["images"][0] for x in items if x.get("images")), None)
        cat["image"] = cover
    CATEGORIES.write_text(json.dumps(categories, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("updated products", len(report))
    for row in report:
        print(f"{row['article']}: {row['before']} -> {row['after']} (-{row['removed']})")
    print("total remaining files", sum(1 for _ in IMG_ROOT.rglob("*.webp")))


if __name__ == "__main__":
    main()
