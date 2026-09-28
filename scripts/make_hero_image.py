# -*- coding: utf-8 -*-
"""Build the homepage hero photo from the untouched Wildberries original.

Source: public/images/products/m-105h/real-01.webp (900x1200, the largest version
that exists anywhere — WB CDN serves no larger "hq/huge" variant). The catalog
01.webp for this SKU went through the aggressive threshold whitening
(scripts/whiten_01_bg.py) plus a second lossy re-encode, which bleached the cream
fabric, ate half of the white bag and softened edges — that is what made the hero
look compressed.

Here we keep every subject pixel from the original, replace only the studio
background with white (rembg u2net + u2net_human_seg mask, despill at edges), and
encode at high quality. No upscaling beyond the original 900 px width.
Outputs (hero only; catalog images/thumbs are not touched):
  public/images/hero/m-105h-900.webp  (q95)
  public/images/hero/m-105h-600.webp  (Lanczos downscale, q92)

Requires: pip install "rembg[cpu]" opencv-python-headless pillow numpy
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "public/images/products/m-105h/real-01.webp"
OUT = ROOT / "public/images/hero"


def mask(img: Image.Image, model: str) -> np.ndarray:
    buf = BytesIO()
    img.save(buf, "PNG")
    cut = remove(buf.getvalue(), session=new_session(model))
    return np.asarray(Image.open(BytesIO(cut)).convert("RGBA"))[:, :, 3].astype(np.float32) / 255.0


def corner_bg(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    s = max(8, min(h, w) // 20)
    samples = np.concatenate([p.reshape(-1, 3) for p in (rgb[:s, :s], rgb[:s, -s:], rgb[-s:, :s], rgb[-s:, -s:])])
    luma = samples.mean(1)
    return np.median(samples[luma > np.percentile(luma, 40)], 0)


def main() -> None:
    real = Image.open(SRC).convert("RGB")
    rgb = np.asarray(real, np.float32)
    a = np.maximum(mask(real, "u2net"), mask(real, "u2net_human_seg"))
    bg = corner_bg(rgb)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    a = cv2.dilate((a * 255).astype(np.uint8), k).astype(np.float32) / 255.0
    a = np.clip(cv2.GaussianBlur(a, (0, 0), 0.7), 0, 1)
    aa = np.maximum(a, 1e-3)
    fg = np.clip((rgb - bg * (1 - aa[..., None])) / aa[..., None], 0, 255)  # despill studio gray
    core = np.clip(cv2.GaussianBlur((a >= 0.92).astype(np.float32), (0, 0), 1.0), 0, 1)[..., None]
    subject = rgb * core + fg * (1 - core)  # original pixels inside the subject
    out = np.clip(subject * a[..., None] + 255 * (1 - a[..., None]), 0, 255).astype(np.uint8)

    OUT.mkdir(parents=True, exist_ok=True)
    full = Image.fromarray(out)
    full.save(OUT / "m-105h-900.webp", "WEBP", quality=95, method=6)
    w, h = full.size
    full.resize((600, round(h * 600 / w)), Image.Resampling.LANCZOS).save(
        OUT / "m-105h-600.webp", "WEBP", quality=92, method=6
    )
    print("wrote", OUT)


if __name__ == "__main__":
    main()
