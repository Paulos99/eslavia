"""Convert AI photoshoot PNGs to webp for catalog."""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("pip install pillow")

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"C:\Users\user\.cursor\projects\c-Users-user-Desktop\assets")
DEST = ROOT / "public" / "images" / "products" / "mtk-116l"
DEST.mkdir(parents=True, exist_ok=True)

pairs = [
    ("mtk-116l-v3-hero.png", "01.webp"),
    ("mtk-116l-v3-window.png", "02.webp"),
    ("mtk-116l-v3-morning.png", "03.webp"),
]

for src_name, dest_name in pairs:
    src = SRC / src_name
    if not src.exists():
        print("skip missing", src)
        continue
    img = Image.open(src).convert("RGB")
    out = DEST / dest_name
    img.save(out, "WEBP", quality=88, method=6)
    print("saved", out, out.stat().st_size)
