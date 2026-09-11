# -*- coding: utf-8 -*-
"""Restore over-whitened catalog heroes from real-01.webp and carefully re-whiten.

Aggressive gray→white thresholding (scripts/whiten_01_bg.py) bleached cream fabric
and left halos. This restores subject pixels from the pre-whiten backup, builds a
person mask with rembg (u2net_human_seg), despills studio-gray fringe, and
composites onto pure white — same idea as the successful М-120Г fix.
"""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]
IMG_ROOT = ROOT / "public" / "images" / "products"

# SKUs reported with blown whites / hair-arm halos after aggressive whitening.
SKUS = [
    "mtk-130v",
    "mtk-130b",
    "mtk-145b",
    "mtk-145s",
    "m-105t",
    "mtk-114k",
    "h-315b",
    "m-105m",
    "m-105sh",
    "n-150s",
]

DILATE_PX = 2
BLUR_SIGMA = 0.7
WEBP_QUALITY = 90
CARD_MAX_SIDE = 960


def corner_bg(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    s = max(8, min(h, w) // 20)
    patches = [arr[:s, :s], arr[:s, -s:], arr[-s:, :s], arr[-s:, -s:]]
    samples = np.concatenate([p.reshape(-1, 3) for p in patches], axis=0)
    luma = samples.mean(axis=1)
    bright = samples[luma > np.percentile(luma, 40)]
    if len(bright) < 10:
        bright = samples
    return np.median(bright.astype(np.float32), axis=0)


def person_alpha(rgb_img: Image.Image, session) -> np.ndarray:
    buf = BytesIO()
    rgb_img.save(buf, format="PNG")
    cut = remove(buf.getvalue(), session=session)
    rgba = np.asarray(Image.open(BytesIO(cut)).convert("RGBA"))
    return rgba[:, :, 3].astype(np.float32) / 255.0


def careful_whiten(rgb: np.ndarray, alpha: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """Keep original subject RGB; only replace background with white after despill."""
    a = alpha.copy()
    if DILATE_PX > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (DILATE_PX * 2 + 1,) * 2)
        a = cv2.dilate((a * 255).astype(np.uint8), k).astype(np.float32) / 255.0
    if BLUR_SIGMA > 0:
        a = cv2.GaussianBlur(a, (0, 0), BLUR_SIGMA)
    a = np.clip(a, 0.0, 1.0)

    eps = 1e-3
    aa = np.maximum(a, eps)
    # Uncompose assumed studio background color (removes gray fringe / halo).
    fg = (rgb - bg * (1.0 - aa[..., None])) / aa[..., None]
    fg = np.clip(fg, 0.0, 255.0)

    # Deep inside the subject keep original pixels (fabric luminance untouched).
    core = (a >= 0.92).astype(np.float32)
    core = cv2.GaussianBlur(core, (0, 0), 1.0)
    core = np.clip(core, 0.0, 1.0)[..., None]
    subject = rgb * core + fg * (1.0 - core)

    out = subject * a[..., None] + 255.0 * (1.0 - a[..., None])
    return np.clip(out, 0.0, 255.0).astype(np.uint8)


def make_card(src: Path, dest: Path) -> None:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    longest = max(w, h)
    if longest > CARD_MAX_SIDE:
        scale = CARD_MAX_SIDE / longest
        im = im.resize(
            (max(1, round(w * scale)), max(1, round(h * scale))),
            Image.Resampling.LANCZOS,
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", quality=82, method=6)


def process_sku(sku: str, session) -> None:
    folder = IMG_ROOT / sku
    real_path = folder / "real-01.webp"
    out_path = folder / "01.webp"
    card_path = folder / "01-card.webp"
    if not real_path.exists():
        raise FileNotFoundError(f"missing backup {real_path}")

    real = Image.open(real_path).convert("RGB")
    rgb = np.asarray(real, dtype=np.float32)
    bg = corner_bg(rgb)
    alpha = person_alpha(real, session)
    out = careful_whiten(rgb, alpha, bg)

    Image.fromarray(out).save(out_path, "WEBP", quality=WEBP_QUALITY, method=4)
    make_card(out_path, card_path)

    # QA metrics vs backup
    mask = alpha >= 0.85
    subj_delta = float(np.mean(np.abs(out.astype(np.float32)[mask] - rgb[mask]))) if mask.any() else 0.0
    cream = mask & (rgb.mean(2) > 200) & (rgb.mean(2) < 248)
    blown = float((out.astype(np.float32)[cream].mean(1) >= 254).mean()) if cream.any() else 0.0
    corner = float(out[:20, :20].mean())
    print(
        f"{sku}: wrote {out_path.relative_to(ROOT)} "
        f"subj_delta={subj_delta:.2f} cream_blown={blown:.3f} corner={corner:.1f}",
        flush=True,
    )


def main() -> int:
    targets = sys.argv[1:] or SKUS
    session = new_session("u2net_human_seg")
    for sku in targets:
        process_sku(sku, session)
    print(f"DONE {len(targets)} SKUs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
