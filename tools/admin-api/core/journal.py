"""Change log of the admin cabinet: data/admin-log.json, written in the same commit as the change.

An entry cannot hold the sha of the commit it lives in, so it keeps `base` (the parent commit, i.e. the
branch head the change was built on). /log resolves base -> commit sha from the history of the log file."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone

from . import catalog as c

LOG = "data/admin-log.json"
MAX_ENTRIES = 1000
MSK = timezone(timedelta(hours=3))

LABELS = {"article": "Артикул", "name": "Название", "category": "Категория", "extraCategories": "Доп. категории",
          "priceWholesale": "Опт", "priceRetail": "Розница", "sizes": "Размеры", "colors": "Цвета",
          "material": "Материал", "availability": "Наличие", "description": "Описание", "sourceUrl": "Ссылка на WB",
          "order": "Порядок на сайте", "photos": "Фото"}
FIELD_ORDER = ["article", "name", "category", "extraCategories", "priceWholesale", "priceRetail", "sizes", "colors",
               "material", "availability", "description", "sourceUrl"]
CUT = 160


def now_iso() -> str:
    return datetime.now(MSK).isoformat(timespec="seconds")


def show(key: str, v) -> str:
    if v is None or v == "" or v == []:
        return ""
    if key in ("priceWholesale", "priceRetail"):
        return c.fmt_price(v) + " ₽"
    if isinstance(v, list):
        s = ", ".join(str(x) for x in v)
    else:
        s = " ".join(str(v).split())
    return s if len(s) <= CUT else s[:CUT].rstrip() + "…"


def _val(p: dict | None, k: str):
    if not p:
        return None
    if k == "extraCategories":
        cats = p.get("categories") or []
        return [x for x in cats if x != p.get("category")]
    v = p.get(k)
    if k in ("priceWholesale", "priceRetail") and v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            return v
    return v


def field_diff(old: dict | None, new: dict) -> list[dict]:
    """Field-level diff of two product records (old None = new model: only the filled fields)."""
    out = []
    for k in FIELD_ORDER:
        a, b = _val(old, k), _val(new, k)
        sa, sb = show(k, a), show(k, b)
        if k == "description" and a and b and " ".join(str(a).split()) != " ".join(str(b).split()) and sa == sb:
            sb += " (изменено)"
        if sa != sb:
            out.append({"field": k, "label": LABELS[k], "old": sa, "new": sb})
    return out


def photo_change(old_imgs: list, new_imgs: list, replaced: list[int], moved: bool = False) -> dict | None:
    n0, n1 = len(old_imgs or []), len(new_imgs or [])
    parts = []
    if replaced:
        nums = ", ".join(str(i + 1) for i in sorted(set(replaced)))
        parts.append(("заменено фото " if len(set(replaced)) == 1 else "заменены фото ") + nums)
    elif moved and n0 == n1:
        parts.append("изменён порядок")
    if n0 != n1 or parts:
        return {"field": "photos", "label": "Фото", "old": f"{n0} шт." if n0 != n1 and n0 else "",
                "new": (f"{n1} шт." if n0 != n1 else "") + ("; " if n0 != n1 and parts else "") + "; ".join(parts)}
    return None


def entry(action: str, p: dict | None = None, changes: list | None = None, note: str = "", src: str = "Кабинет",
          **extra) -> dict:
    e = {"t": now_iso(), "action": action}
    if p:
        e.update(id=p.get("id"), article=p.get("article"), name=p.get("name"))
    if changes:
        e["changes"] = changes
    if note:
        e["note"] = note
    e["src"] = src
    e.update({k: v for k, v in extra.items() if v not in (None, "", [])})
    return e


def read(repo) -> dict:
    try:
        log = repo.read_json(LOG, default={"version": 1, "entries": []})
    except (ValueError, KeyError):
        log = {"version": 1, "entries": []}
    log.setdefault("entries", [])
    return log


def append(repo, entries: list[dict]) -> bytes:
    """Return the new log file for a commit on top of repo.head (call after repo.load_head())."""
    log = read(repo)
    batch = secrets.token_hex(4)
    for e in entries:
        e["base"] = repo.head
        e["batch"] = batch
    log["entries"] = (log["entries"] + entries)[-MAX_ENTRIES:]
    return (json.dumps(log, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


_SHA_CACHE: dict[str, str] = {}


def resolve(repo, bases: set[str], pages: int = 5) -> dict[str, str]:
    """base (parent) -> sha of the commit that wrote the entry, from the history of the log file."""
    need = {b for b in bases if b and b not in _SHA_CACHE}
    page = 1
    while need and page <= pages:
        try:
            r = repo._req("GET", f"/commits?sha={repo.branch}&path={LOG}&per_page=100&page={page}").json()
        except Exception:  # noqa: BLE001
            break
        if not r:
            break
        for cm in r:
            for par in cm.get("parents") or []:
                _SHA_CACHE[par["sha"]] = cm["sha"]
        need = {b for b in need if b not in _SHA_CACHE}
        page += 1
    return {b: _SHA_CACHE[b] for b in bases if b in _SHA_CACHE}


GROUPS = {"edit": {"edit", "import-edit"}, "add": {"add", "import-add"}, "delete": {"delete", "import-delete"},
          "import": {"import", "import-edit", "import-add", "import-delete"}, "tg": {"tg", "nav", "blank-done"}}


def query(repo, model: str = "", action: str = "", offset: int = 0, limit: int = 50) -> dict:
    log = read(repo)
    items = list(reversed(log["entries"]))
    m = (model or "").strip().lower()
    if m:
        items = [e for e in items if m in " ".join(str(e.get(k) or "") for k in ("article", "id", "name")).lower()
                 or (e.get("action") == "import" and m in " ".join(e.get("articles") or []).lower())]
    if action:
        acts = GROUPS.get(action, {action})
        items = [e for e in items if e.get("action") in acts]
    total = len(items)
    offset, limit = max(0, int(offset or 0)), max(1, min(200, int(limit or 50)))
    page = [dict(e) for e in items[offset:offset + limit]]
    shas = resolve(repo, {e.get("base") for e in page})
    for e in page:
        e["sha"] = shas.get(e.get("base"))
        e.pop("batch", None)
    return {"entries": page, "total": total, "offset": offset, "limit": limit, "repo": repo.full_name}
