import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(r"C:\Users\user\.cursor\projects\c-Users-user-Desktop\assets")
products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "data/ai-photoshoot-manifest.json").read_text(encoding="utf-8"))
SKIP = {"mtk-116l"}

issues = []
fixed = 0

for entry in manifest:
    pid = entry["id"]
    dest = Path(entry["ai_output"])
    if pid in SKIP and dest.exists():
        continue
    src = ASSETS / f"ai-{pid}.png"
    if not src.exists():
        alts = list((ROOT / "public/images/products" / pid).glob("ai-*.png"))
        src = alts[0] if alts else None
    if src and src.exists() and (not dest.exists() or dest.stat().st_size < 5000):
        im = Image.open(src).convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "WEBP", quality=88, method=6)
        fixed += 1
        print("fixed webp", pid)
    elif not dest.exists():
        issues.append(f"missing 01.webp: {pid}")

by_id = {p["id"]: p for p in products}
for entry in manifest:
    pid = entry["id"]
    reals = entry.get("real_images") or []
    hero = f"/images/products/{pid}/01.webp"
    if pid in SKIP:
        by_id[pid]["images"] = [hero] + reals[:2]
    else:
        by_id[pid]["images"] = [hero] + reals

for p in products:
    imgs = p.get("images") or []
    if not imgs:
        issues.append(f"empty images: {p['id']}")
        continue
    p01 = ROOT / "public" / imgs[0].lstrip("/")
    if not p01.exists():
        issues.append(f"missing file: {p['id']} -> {imgs[0]}")

(ROOT / "data/products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
cats = json.loads((ROOT / "data/categories.json").read_text(encoding="utf-8"))
for c in cats:
    items = [p for p in products if p["category"] == c["name"]]
    c["image"] = next((p["images"][0] for p in items if p.get("images")), None)
(ROOT / "data/categories.json").write_text(json.dumps(cats, ensure_ascii=False, indent=2), encoding="utf-8")

print("fixed", fixed)
print("issues", len(issues))
for i in issues:
    print(" -", i)
print("all ok" if not issues else "needs attention")
