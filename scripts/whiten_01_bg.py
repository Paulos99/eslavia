# -*- coding: utf-8 -*-
"""Whiten studio backgrounds on product 01.webp only."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(r"C:\Users\user\Desktop\Организация\Проекты\КОДИНГ\таисия")
PRODUCTS = ROOT / "public" / "images" / "products"
DIST_THRESH = 38.0
SOFT = 18.0
MIN_LUMA = 175


def corner_bg(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    s = max(8, min(h, w) // 20)
    patches = [arr[:s, :s], arr[:s, -s:], arr[-s:, :s], arr[-s:, -s:]]
    samples = np.concatenate([p.reshape(-1, 3) for p in patches], axis=0)
    luma = samples.astype(np.float32).mean(axis=1)
    bright = samples[luma > np.percentile(luma, 40)]
    if len(bright) < 10:
        bright = samples
    return np.median(bright.astype(np.float32), axis=0)


def whiten(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    arr = np.asarray(rgb, dtype=np.float32)
    bg = corner_bg(arr)
    if float(bg.mean()) >= 252 and float(np.abs(arr[:20, :20] - 255).mean()) < 4:
        return rgb
    dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))
    luma = arr.mean(axis=2)
    t0, t1 = DIST_THRESH, DIST_THRESH + SOFT
    strength = np.clip((t1 - dist) / (t1 - t0), 0, 1)
    strength = strength * (luma >= MIN_LUMA).astype(np.float32)
    near_white = (luma >= 230) & (arr.max(axis=2) - arr.min(axis=2) < 18)
    strength = np.maximum(strength, near_white.astype(np.float32) * 0.85)
    strength3 = strength[..., None]
    out = arr * (1 - strength3) + 255.0 * strength3
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def make_card(src: Image.Image, size: int = 480) -> Image.Image:
    w, h = src.size
    side = min(w, h)
    left = (w - side) // 2
    top = max(0, (h - side) // 3)
    if top + side > h:
        top = h - side
    crop = src.crop((left, top, left + side, top + side))
    return crop.resize((size, size), Image.Resampling.LANCZOS)


def main() -> int:
    dirs = sorted([p for p in PRODUCTS.iterdir() if p.is_dir()])
    done = skipped = failed = 0
    for d in dirs:
        src_path = d / "01.webp"
        if not src_path.exists():
            skipped += 1
            continue
        try:
            img = Image.open(src_path)
            out = whiten(img)
            out.save(src_path, "WEBP", quality=90, method=4)
            make_card(out).save(d / "01-card.webp", "WEBP", quality=85, method=4)
            done += 1
            if done % 20 == 0:
                print(f"... {done}/{len(dirs)}", flush=True)
        except Exception as e:
            failed += 1
            print(f"FAIL {d.name}: {e}", flush=True)
    print(f"DONE whitened={done} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())