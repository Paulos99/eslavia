"""Image conversions, identical in spirit to scripts/make_grid_thumbs.py, build_data.py and post_catalog.py."""
from __future__ import annotations

import base64
import io

from PIL import Image, ImageOps

FULL = (900, 1200)
MAX_UPLOAD = 12 * 1024 * 1024


def _open(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


def decode_upload(b64: str) -> bytes:
    if "," in b64[:100]:
        b64 = b64.split(",", 1)[1]
    data = base64.b64decode(b64, validate=False)
    if len(data) > MAX_UPLOAD:
        raise ValueError("фото слишком большое")
    return data


def normalize_original(data: bytes) -> bytes:
    """Any photo -> 900x1200 WebP (3:4). Other aspect ratios are fitted on white, nothing is cropped."""
    im = _open(data)
    w, h = im.size
    if w < 300 or h < 400:
        raise ValueError(f"фото слишком маленькое ({w}×{h}), нужно хотя бы 600×800")
    if abs(w / h - 0.75) > 0.02:
        scale = min(FULL[0] / w, FULL[1] / h)
        fitted = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", FULL, (255, 255, 255))
        canvas.paste(fitted, ((FULL[0] - fitted.width) // 2, (FULL[1] - fitted.height) // 2))
        im = canvas
    elif im.size != FULL:
        im = im.resize(FULL, Image.Resampling.LANCZOS)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=86, method=6)
    return out.getvalue()


def webp_width(data: bytes, width: int, quality: int = 82) -> bytes:
    im = _open(data)
    w, h = im.size
    if w > width:
        im = im.resize((width, round(h * width / w)), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=quality, method=6)
    return out.getvalue()


def tg_jpeg(data: bytes) -> bytes:
    im = _open(data)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=92, subsampling=0, optimize=True)
    return out.getvalue()


def price_thumb(data: bytes) -> bytes:
    im = _open(data).resize((180, 240), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=80, optimize=True)
    return out.getvalue()
