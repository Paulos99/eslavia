"""Set MTK-116L: 01 = approved AI window photo, 02-03 = real shoot."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "public" / "images" / "products" / "mtk-116l"
AI_SRC = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop\assets\mtk-116l-v3-window.png"
)
REAL = [
    (DEST / "ref-03.jpg", "02.webp"),
    (DEST / "ref-05.jpg", "03.webp"),
]

def to_webp(src: Path, name: str) -> None:
    img = Image.open(src).convert("RGB")
    out = DEST / name
    img.save(out, "WEBP", quality=88, method=6)
    print(f"saved {out} ({out.stat().st_size} bytes) from {src.name}")

if AI_SRC.exists():
    to_webp(AI_SRC, "01.webp")
else:
    fallback = Path(r"C:\Users\user\.cursor\projects\c-Users-user-Desktop\assets\mtk-116l-v3-window.png")
    to_webp(fallback, "01.webp")

for src, name in REAL:
    if src.exists():
        to_webp(src, name)
