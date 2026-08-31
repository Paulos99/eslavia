# -*- coding: utf-8 -*-
"""Download real photos as 02+ and build AI generation manifest for all SKUs."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_PATH = ROOT / "data" / "products.json"
IMG_ROOT = ROOT / "public" / "images" / "products"
MANIFEST_PATH = ROOT / "data" / "ai-photoshoot-manifest.json"
UA = "Mozilla/5.0 (compatible; TaisiyaCatalogAudit/1.0)"
SKIP_AI = {"mtk-116l"}  # already approved

MODELS = [
    "Woman 32, shoulder-length wavy auburn hair, fair skin, soft freckles, green eyes",
    "Woman 34, short dark blonde bob, light olive skin, warm brown eyes, round face",
    "Woman 36, curly brown hair in low bun, medium skin tone, kind expression, average build",
    "Woman 38, straight chestnut hair to shoulders, light skin, subtle smile, size 52 build",
    "Woman 35, silver-streaked dark hair in ponytail, warm complexion, confident look",
    "Woman 33, black curly hair shoulder length, deep brown skin, natural glow",
]

CATEGORY_SCENES = {
    "Пижамы для дома": (
        "Sitting on wide window sill with ceramic coffee mug, golden hour sunlight through window, "
        "modern apartment, monstera plant nearby, cream walls. INDOORS ONLY — home coziness, comfort, morning ritual."
    ),
    "Платья": (
        "Walking gracefully on sunlit cobblestone street or garden path, soft breeze in dress fabric, "
        "golden hour, shallow depth of field, effortless elegance and lightness. OUTDOORS — beauty and freedom."
    ),
    "Сарафаны": (
        "Standing on sunny terrace or meadow edge, wind gently moving sarafan fabric, warm natural light, "
        "joyful relaxed smile. OUTDOORS — summer lightness and feminine beauty."
    ),
    "Костюмы": (
        "Lounging on cream bouclé sofa in bright loft apartment, legs tucked, natural relaxed pose, "
        "golden hour through large window, urban view blurred. INDOORS — comfortable stylish home life."
    ),
    "Туники": (
        "Near sunlit window in minimalist home, soft side light, relaxed standing pose, "
        "easy everyday comfort. INDOORS — casual elegance at home."
    ),
    "Толстовки": (
        "Casual moment in modern loft, coffee in hand, relaxed smile, warm indoor light. "
        "INDOORS — cozy everyday comfort."
    ),
    "Халаты": (
        "Morning scene by bathroom door or bedroom window, soft bathrobe moment, golden light, "
        "pure home comfort. INDOORS ONLY."
    ),
    "Сорочки": (
        "Soft morning light in bedroom near window, intimate home comfort, gentle pose. INDOORS ONLY."
    ),
    "Футболки": (
        "Bright casual moment at home near window or on balcony, natural smile, everyday ease."
    ),
    "Водолазки": (
        "Autumn window light indoors, cozy layered look, warm drink, hygge atmosphere. INDOORS."
    ),
    "Топы": (
        "Sunlit home interior, relaxed summer mood near open window, natural beauty."
    ),
    "Велосипедки": (
        "Active casual moment — home yoga stretch or sunny balcony, comfortable movement."
    ),
}


def encode_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/()")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(encode_url(url), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.read()
    except Exception:
        return b""


def fetch_page_images(url: str) -> list[str]:
    try:
        req = urllib.request.Request(encode_url(url), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as res:
            html = res.read().decode("utf-8", "replace")
    except Exception:
        return []
    urls = re.findall(r"https?://[^\"'\\s]+\\.(?:jpg|jpeg|png|webp)", html, re.I)
    # prefer large cache images
    large = [u for u in urls if "751x1000" in u or "400x533" in u]
    other = [u for u in urls if u not in large and "favicon" not in u.lower()]
    seen: set[str] = set()
    out: list[str] = []
    for u in large + other:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out[:6]


def to_webp(data: bytes, dest: Path) -> bool:
    try:
        im = Image.open(BytesIO(data))
        if im.mode != "RGB":
            im = im.convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "WEBP", quality=88, method=6)
        return True
    except Exception:
        return False


def pick_model(idx: int) -> str:
    return MODELS[idx % len(MODELS)]


def product_garment_hint(product: dict) -> str:
    name = product.get("name", "")
    material = product.get("material") or "cotton knit"
    colors = ", ".join(product.get("colors") or []) or "as shown in reference"
    return (
        f"Wearing {name} — {material}, colors: {colors}. "
        "Match exact color, pattern and cut from product reference photo only, not the model."
    )


def build_prompt(product: dict, model_idx: int) -> str:
    cat = product.get("category") or "Платья"
    scene = CATEGORY_SCENES.get(cat, CATEGORY_SCENES["Платья"])
    model = pick_model(model_idx)
    garment = product_garment_hint(product)
    return (
        "Editorial fashion e-commerce photography, Gorde-inspired 'Casual But Fancy'. "
        "Original fictional model ONLY — do NOT replicate likeness of any real person. "
        f"{model}. {garment} "
        f"Scene: {scene} "
        "Shallow depth of field, warm earthy palette cream terracotta sage, cinematic natural light. "
        "NOT white brick wall, NOT catalog stiff mannequin pose, NOT harsh studio flash. "
        "3:4 vertical photorealistic editorial."
    )


def download_reals(product: dict) -> tuple[list[str], Path | None]:
    pid = product["id"]
    folder = IMG_ROOT / pid
    folder.mkdir(parents=True, exist_ok=True)

    # collect existing non-AI webp/jpeg as fallback
    existing: list[Path] = sorted(
        [p for p in folder.glob("*") if p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"} and not p.name.startswith("ai-")],
        key=lambda p: p.name,
    )

    urls = fetch_page_images(product.get("sourceUrl") or "")
    saved_paths: list[Path] = []

    # download from site
    for i, url in enumerate(urls, 1):
        blob = fetch_bytes(url)
        if len(blob) < 800:
            continue
        dest = folder / f"real-{i:02d}.webp"
        if to_webp(blob, dest):
            saved_paths.append(dest)
        time.sleep(0.2)

    if not saved_paths and existing:
        for i, src in enumerate(existing, 1):
            dest = folder / f"real-{i:02d}.webp"
            if src.resolve() == dest.resolve():
                saved_paths.append(dest)
                continue
            im = Image.open(src)
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.save(dest, "WEBP", quality=88, method=6)
            saved_paths.append(dest)

    # renumber reals to 02+, keep ref copy for AI
    ref_path: Path | None = None
    image_paths: list[str] = []
    for i, src in enumerate(saved_paths, 2):
        dest = folder / f"{i:02d}.webp"
        im = Image.open(src)
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.save(dest, "WEBP", quality=88, method=6)
        image_paths.append(f"/images/products/{pid}/{dest.name}")
        if i == 2:
            ref_path = folder / "ref-for-ai.webp"
            im.save(ref_path, "WEBP", quality=90, method=6)

    return image_paths, ref_path


def main() -> None:
    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    manifest: list[dict] = []

    for idx, product in enumerate(products):
        pid = product["id"]
        print(f"[{idx+1}/{len(products)}] {pid} …", flush=True)

        real_paths, ref_path = download_reals(product)

        if pid in SKIP_AI:
            ai_path = IMG_ROOT / pid / "01.webp"
            if ai_path.exists():
                images = [f"/images/products/{pid}/01.webp"] + real_paths
                product["images"] = images
                print(f"  skip AI, keep approved 01 + {len(real_paths)} reals")
                continue

        if not ref_path or not ref_path.exists():
            # try any 02
            candidate = IMG_ROOT / pid / "02.webp"
            ref_path = candidate if candidate.exists() else None

        entry = {
            "id": pid,
            "article": product.get("article"),
            "name": product.get("name"),
            "category": product.get("category"),
            "prompt": build_prompt(product, idx),
            "ref_path": str(ref_path) if ref_path else None,
            "real_images": real_paths,
            "ai_output": str(IMG_ROOT / pid / "01.webp"),
        }
        manifest.append(entry)
        print(f"  reals: {len(real_paths)}, ref: {bool(ref_path)}")

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # update products with real-only paths temporarily (01 filled after AI gen)
    for product in products:
        pid = product["id"]
        if pid in SKIP_AI:
            continue
        reals = [e["real_images"] for e in manifest if e["id"] == pid]
        if reals:
            product["images"] = reals[0]  # without 01 until AI done

    PRODUCTS_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest: {len(manifest)} SKUs → {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
