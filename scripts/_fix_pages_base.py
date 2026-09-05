# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(r"C:\Users\user\Desktop\Организация\Проекты\КОДИНГ\таисия")
DIST = ROOT / "dist"
WORK = ROOT / ".gh-pages-deploy-tmp"
REMOTE = "https://github.com/Paulos99/eslavia.git"

# Fix vite.config.ts base fallback
vite = ROOT / "vite.config.ts"
text = vite.read_text(encoding="utf-8")
new = re.sub(
    r"base:\s*repoName\s*\?\s*`/\$\{repoName\}/`\s*:\s*[\"']/[\"']",
    "base: repoName ? `/${repoName}/` : '/eslavia/'",
    text,
)
if new != text:
    vite.write_text(new, encoding="utf-8")
    print("vite.config.ts base fallback -> /eslavia/")
else:
    print("vite.config.ts already ok or pattern miss")
    # show current base line
    for line in text.splitlines():
        if "base:" in line:
            print(" ", line.strip())

# Patch dist HTML
for name in ("index.html", "404.html"):
    p = DIST / name
    if not p.exists():
        continue
    html = p.read_text(encoding="utf-8")
    html2 = html.replace('src="/assets/', 'src="/eslavia/assets/').replace(
        'href="/assets/', 'href="/eslavia/assets/'
    )
    p.write_text(html2, encoding="utf-8")
    print("patched", name)
    for line in html2.splitlines():
        if "assets/" in line:
            print(" ", line.strip())

# Deploy
if WORK.exists():
    for i in range(8):
        try:
            shutil.rmtree(WORK)
            break
        except Exception as e:
            print("rmtree", e)
            time.sleep(1)
            subprocess.run(["cmd", "/c", f'rmdir /s /q "{WORK}"'], check=False)
    else:
        raise SystemExit("cannot clear WORK")
WORK.mkdir()
subprocess.run(
    ["git", "clone", "--branch", "gh-pages", "--single-branch", REMOTE, str(WORK)],
    check=True,
)
for item in list(WORK.iterdir()):
    if item.name == ".git":
        continue
    if item.is_dir():
        shutil.rmtree(item)
    else:
        item.unlink()
for item in DIST.iterdir():
    dest = WORK / item.name
    if item.is_dir():
        shutil.copytree(item, dest)
    else:
        shutil.copy2(item, dest)
(WORK / ".nojekyll").touch()
subprocess.run(["git", "add", "-A"], cwd=WORK, check=True)
st = subprocess.run(
    ["git", "status", "--porcelain"], cwd=WORK, capture_output=True, text=True
)
print(st.stdout[:800] if st.stdout else "(clean)")
if not st.stdout.strip():
    print("Nothing to deploy")
else:
    subprocess.run(
        ["git", "commit", "-m", "fix(pages): restore /eslavia/ asset base paths"],
        cwd=WORK,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "gh-pages"], cwd=WORK, check=True)
    print("Deployed")