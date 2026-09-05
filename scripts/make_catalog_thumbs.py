# -*- coding: utf-8 -*-
"""Downscale catalog previews without cropping (Lanczos + light blur to reduce moiré)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
IMG_ROOT = ROOT / "public" / "images" / "products"
MAX_SIDE = 960


def card_path(src: Path) -> Path:
    return src.with_name(f"{src.stem}-card{src.suffix}")


def make_card(src: Path, dest: Path | None = None) -> bool:
    if not src.exists():
        return False
    dest = dest or card_path(src)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    longest = max(w, h)
    if longest > MAX_SIDE:
        scale = MAX_SIDE / longest
        im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)
        im = im.filter(ImageFilter.GaussianBlur(radius=0.45))
    elif longest > 480:
        im = im.filter(ImageFilter.GaussianBlur(radius=0.35))
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", quality=82, method=6)
    return True


def main() -> None:
    n = 0
    for folder in sorted(IMG_ROOT.iterdir()):
        if not folder.is_dir():
            continue
        for name in ("01.webp", "02.webp", "studio.webp"):
            src = folder / name
            if src.exists() and make_card(src):
                n += 1
                print("thumb", src.relative_to(ROOT))
    print(f"wrote {n} thumbs")


if __name__ == "__main__":
    main()
