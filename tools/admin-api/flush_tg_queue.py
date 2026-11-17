"""Send queued channel updates (data/tg-queue.json) from a machine that can reach api.telegram.org.

Yandex Cloud Functions cannot reach Telegram (api.telegram.org is filtered there), so the admin function
queues failed post updates in the repo. Run this from any machine with Telegram access:

    GITHUB_TOKEN=... TG_TOKEN_FILE=~/.secrets/eslavia_opt_bot.token python flush_tg_queue.py [--list]

Runs automatically in GitHub Actions: .github/workflows/tg-queue.yml (TG_TOKEN from repo secrets).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core.pipeline import Pipeline  # noqa: E402


def main() -> None:
    token_file = os.environ.get("TG_TOKEN_FILE", "")
    cfg = {
        "SITE_REPO": os.environ.get("SITE_REPO", "Paulos99/eslavia"), "SITE_BRANCH": os.environ.get("SITE_BRANCH", "main"),
        "APP_REPO": os.environ.get("APP_REPO", "Paulos99/eslavia-app"), "APP_BRANCH": os.environ.get("APP_BRANCH", "main"),
        "GITHUB_TOKEN": os.environ["GITHUB_TOKEN"].strip(), "GITHUB_DRY_RUN": False,
        "TG_TOKEN": (os.environ.get("TG_TOKEN") or "").strip()
        or (Path(token_file).expanduser().read_text().strip() if token_file else None),
        "TG_CHAT_ID": os.environ.get("TG_CHAT_ID", "-1004469691410"), "TG_DRY_RUN": False,
        "IMAGE_BASE": "https://eslavia.ru",
    }
    pipe = Pipeline(cfg)
    if "--list" in sys.argv:
        print(json.dumps(pipe.listing()["tgQueue"], ensure_ascii=False, indent=1))
        return
    res = pipe.tg_retry(commit_suffix=os.environ.get("COMMIT_SUFFIX", ""))
    res.pop("dry_run", None)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:  # for the workflow: redeploy Pages only when the Mini App catalog got new post links
        with open(out, "a") as f:
            f.write(f"posts_changed={'true' if res.get('postsChanged') else 'false'}\n")
            f.write(f"left={res.get('left', 0)}\n")
    if res.get("ok") is False and res.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
