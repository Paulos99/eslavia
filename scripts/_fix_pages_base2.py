# -*- coding: utf-8 -*-
from pathlib import Path
import shutil, subprocess, time
ROOT = Path(r"C:\Users\user\Desktop\Организация\Проекты\КОДИНГ\таисия")
DIST = ROOT / "dist"
WORK = ROOT / ".gh-pages-deploy-tmp2"
REMOTE = "https://github.com/Paulos99/eslavia.git"
if WORK.exists():
    shutil.rmtree(WORK, ignore_errors=True)
    time.sleep(1)
if WORK.exists():
    raise SystemExit("work2 still exists")
subprocess.run(["git","clone","--branch","gh-pages","--single-branch",REMOTE,str(WORK)], check=True)
# only update index.html and 404.html for speed/safety — but full sync is fine
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
subprocess.run(["git","add","-A"], cwd=WORK, check=True)
st = subprocess.run(["git","status","--porcelain"], cwd=WORK, capture_output=True, text=True)
print(st.stdout[:1000] if st.stdout else "(clean)")
if not st.stdout.strip():
    print("Nothing to deploy")
else:
    subprocess.run(["git","commit","-m","fix(pages): restore /eslavia/ asset base paths"], cwd=WORK, check=True)
    subprocess.run(["git","push","origin","gh-pages"], cwd=WORK, check=True)
    print("Deployed")
# verify local patched content is what we expect
idx = (DIST/"index.html").read_text(encoding="utf-8")
assert "/eslavia/assets/" in idx, "dist still wrong"
print("dist assert ok")