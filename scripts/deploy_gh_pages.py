# -*- coding: utf-8 -*-
"""Deploy dist/ to gh-pages branch (project site paulos99.github.io/eslavia/)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REMOTE = "https://github.com/Paulos99/eslavia.git"
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
WORK = ROOT / ".gh-pages-deploy-tmp"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def main() -> None:
    if not DIST.exists():
        raise SystemExit("dist/ missing — run build first")

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()

    run(["git", "clone", "--branch", "gh-pages", "--single-branch", REMOTE, str(WORK)])

    for item in WORK.iterdir():
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

    run(["git", "add", "-A"], cwd=WORK)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=WORK, capture_output=True, text=True)
    if not status.stdout.strip():
        print("Nothing to deploy")
        return

    run(["git", "commit", "-m", "deploy: Эславия rebrand"], cwd=WORK)
    run(["git", "push", "origin", "gh-pages"], cwd=WORK)
    print("Deployed to gh-pages")


if __name__ == "__main__":
    main()
