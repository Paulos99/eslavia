"""Save / delete a product: site repo (one commit) + price PDF + Mini App + Telegram."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

from . import appcat, catalog as c, images, pdfgen, xlsx
from .gh import GitHubError, Repo
from .tg import Telegram, TgError

PRODUCTS = "data/products.json"
CATEGORIES = "data/categories.json"
TG_POSTS = "data/tg-posts.json"
TG_QUEUE = "data/tg-queue.json"
CAPTION_KEYS = ("name", "article", "sizes", "priceWholesale", "category")
TG_PAUSE = 0.35
PRICE_THUMBS = "data/price-thumbs"
PDF = "public/prices/optovyy-prays.pdf"
IMG = "public/images/products"
THUMBS = "public/images/thumbs"
SITE_APP = "public/app"
NN_RE = re.compile(r"^\d\d\.webp$")
TEXT_FIELDS = ("article", "name", "category", "material", "description", "availability")


class UserError(Exception):
    pass


def dumps_pretty(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


class Pipeline:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    # -- repos ------------------------------------------------------------
    def site(self) -> Repo:
        return Repo(self.cfg["SITE_REPO"], self.cfg["SITE_BRANCH"], self.cfg.get("GITHUB_TOKEN"),
                    dry_run=self.cfg["GITHUB_DRY_RUN"])

    def app(self) -> Repo | None:
        if not self.cfg.get("APP_REPO"):
            return None
        return Repo(self.cfg["APP_REPO"], self.cfg["APP_BRANCH"], self.cfg.get("GITHUB_TOKEN"),
                    dry_run=self.cfg["GITHUB_DRY_RUN"])

    def tg(self) -> Telegram:
        return Telegram(self.cfg.get("TG_TOKEN"), self.cfg["TG_CHAT_ID"], dry_run=self.cfg["TG_DRY_RUN"],
                        simulate_down=self.cfg.get("TG_SIMULATE_DOWN", False))

    def _state(self, repo: Repo):
        products = repo.read_json(PRODUCTS)
        cats = repo.read_json(CATEGORIES)
        posts = repo.read_json(TG_POSTS, default={"version": 1, "chat_id": int(self.cfg["TG_CHAT_ID"]),
                                                   "channel": c.CHANNEL, "posts": {}})
        return products, cats, posts

    # -- read -------------------------------------------------------------
    def listing(self) -> dict:
        repo = self.site()
        head = repo.load_head()
        products, cats, posts = self._state(repo)
        for p in products:
            p["_post"] = appcat.post_url(posts, p["id"])
        queue = self._queue(repo)
        arts = {p["id"]: p.get("article") for p in products}
        return {"tgQueue": [{"id": k, **v, "article": arts.get(k) or v.get("article") or k} for k, v in queue["items"].items()],
                "products": products, "categories": [x["name"] for x in cats] or c.CATEGORIES,
                "head": head, "repo": self.cfg["SITE_REPO"], "imageBase": self.cfg["IMAGE_BASE"],
                "rawBase": f"https://raw.githubusercontent.com/{self.cfg['SITE_REPO']}/{head}/public",
                "dryRun": {"github": self.cfg["GITHUB_DRY_RUN"], "telegram": self.cfg["TG_DRY_RUN"]}}

    def status(self, sha: str) -> dict:
        return self.site().pages_status(sha)

    # -- validation -------------------------------------------------------
    @staticmethod
    def clean_product(raw: dict) -> dict:
        def s(k, maxlen=300):
            v = raw.get(k)
            v = "" if v is None else re.sub(r"\s+", " ", str(v)).strip()
            if len(v) > maxlen:
                raise UserError(f"Поле «{k}» слишком длинное")
            return v
        out = {"article": s("article", 40), "name": s("name", 120), "category": s("category", 60),
               "material": s("material", 120), "availability": s("availability", 60) or "Есть в наличии"}
        desc = raw.get("description") or ""
        out["description"] = str(desc).strip()[:3000]
        if not out["article"]:
            raise UserError("Укажите артикул")
        if not re.search(r"[0-9A-Za-zА-Яа-яЁё]", out["article"]):
            raise UserError("Артикул должен содержать буквы или цифры")
        if not out["name"]:
            raise UserError("Укажите название")
        if out["category"] not in c.CATEGORIES:
            raise UserError("Выберите категорию из списка")
        for k, label in (("priceWholesale", "оптовую цену"), ("priceRetail", "розничную цену")):
            try:
                v = float(str(raw.get(k, "")).replace(" ", "").replace(",", "."))
            except ValueError:
                raise UserError(f"Укажите {label} числом")
            if not (0 < v < 1_000_000):
                raise UserError(f"Укажите {label}")
            out[k] = float(round(v, 2))
        sizes = [re.sub(r"\s+", "", str(x)) for x in raw.get("sizes") or [] if str(x).strip()]
        if not sizes:
            raise UserError("Отметьте хотя бы один размер")
        for x in sizes:
            if not re.fullmatch(r"\d{2}(-\d{2})?", x):
                raise UserError(f"Размер «{x}» записан непонятно: нужно 52 или 50-52")
        out["sizes"] = list(dict.fromkeys(sizes))
        out["colors"] = [str(x).strip().lower() for x in raw.get("colors") or [] if str(x).strip()][:20]
        for bad in ("производств", "производител"):
            for k in ("name", "description", "material"):
                if bad in out[k].lower():
                    raise UserError("В текстах карточки не используем слова «производство» и «производитель»")
        return out

    # -- save -------------------------------------------------------------
    def save(self, payload: dict, progress=lambda *_: None) -> dict:
        t0 = time.time()
        fields = self.clean_product(payload.get("product") or {})
        orig_id = payload.get("id") or None
        photos = payload.get("photos") or []
        if not (3 <= len(photos) <= 8):
            raise UserError("Нужно от 3 до 8 фото: первые три уходят в пост канала")
        uploads: dict[int, bytes] = {}
        for i, ph in enumerate(photos):
            if ph.get("data"):
                try:
                    uploads[i] = images.normalize_original(images.decode_upload(ph["data"]))
                except Exception as e:  # noqa: BLE001
                    raise UserError(f"Фото {i + 1}: не удалось прочитать ({e})")
            elif not ph.get("keep"):
                raise UserError("Пустое фото в списке")
        report = {"steps": [], "warnings": []}
        new_msg_ids: list[int] | None = None
        tg = self.tg()
        tg_ok = None
        last_err = None
        for attempt in range(3):
            repo = self.site()
            repo.load_head()
            products, cats, posts = self._state(repo)
            by_id = {p["id"]: p for p in products}
            old = by_id.get(orig_id) if orig_id else None
            if orig_id and not old:
                raise UserError("Эта модель уже удалена или переименована, обновите список")
            pid = old["id"] if old else c.product_id(fields["article"])
            if not old:
                if not pid:
                    raise UserError("Не получилось сделать адрес карточки из артикула")
                if pid in by_id:
                    raise UserError(f"Модель с артикулом {fields['article']} уже есть")
            for p in products:
                if p is not old and (p.get("article") or "").strip().lower() == fields["article"].lower():
                    raise UserError(f"Артикул {fields['article']} уже занят другой моделью")
            if payload.get("baseHead") and old and attempt == 0 and payload["baseHead"] != repo.head:
                # someone saved in between: fine, we re-read; only the edited product is replaced
                report["warnings"].append("Каталог успели изменить параллельно, правка применена к свежей версии")

            # ---- images
            files: dict[str, object] = {}
            final_imgs, src_ref = [], []   # src_ref[i] = ("blob", sha) | ("new", bytes)
            for i, ph in enumerate(photos):
                target = f"/images/products/{pid}/{i + 1:02d}.webp"
                final_imgs.append(target)
                if i in uploads:
                    files["public" + target] = uploads[i]
                    src_ref.append(("new", uploads[i]))
                else:
                    keep = ph["keep"]
                    if not old or keep not in (old.get("images") or []):
                        raise UserError("Одно из старых фото не найдено, обновите страницу")
                    sha = repo.tree.get("public" + keep)
                    if not sha:
                        raise UserError(f"Файл {keep} не найден в репозитории")
                    if keep != target:
                        files["public" + target] = {"sha": sha}
                    src_ref.append(("blob", sha))
            if old:
                for path in old.get("images") or []:
                    if ("public" + path) not in files and path not in final_imgs:
                        if NN_RE.match(path.rsplit("/", 1)[-1]):
                            files["public" + path] = None
            old_first = [repo.tree.get("public" + x) for x in (old.get("images") or [])[:3]] if old else []
            new_first = [r[1] if r[0] == "blob" else None for r in src_ref[:3]]
            photos_changed = [i for i in range(3) if not old or i >= len(old_first) or new_first[i] != old_first[i]]
            thumb_changed = 0 in photos_changed or (old and 1 in photos_changed)

            # ---- product record
            prod = dict(old) if old else {"id": pid}
            for k in TEXT_FIELDS:
                was = old.get(k) if old else None
                norm_was = re.sub(r"\s+", " ", str(was or "")).strip()
                norm_new = re.sub(r"\s+", " ", str(fields[k] or "")).strip()
                if old and norm_was == norm_new:
                    continue  # unchanged: keep the stored value byte-for-byte (None stays None)
                prod[k] = fields[k]
            for k in ("priceRetail", "priceWholesale", "sizes", "colors"):
                if old and k in ("priceRetail", "priceWholesale") and float(old.get(k) or 0) == fields[k]:
                    continue
                prod[k] = fields[k]
            if not old or prod.get("categories") in (None, [], [old.get("category")]):
                prod["categories"] = [fields["category"]]
            prod["images"] = final_imgs
            ordered_keys = ["id", "article", "name", "category", "categories", "priceRetail", "priceWholesale",
                            "sizes", "colors", "material", "description", "availability", "images"]
            prod = {k: prod[k] for k in ordered_keys if k in prod} | {k: v for k, v in prod.items() if k not in ordered_keys}
            if not prod.get("material") and not (old and "material" in old):
                prod.pop("material", None)
            if old:
                products = [prod if p is old else p for p in products]
            else:
                idx = max([i for i, p in enumerate(products) if p.get("category") == prod["category"]], default=len(products) - 1)
                products.insert(idx + 1, prod)
            cats_new = c.recount_categories(cats, products)

            # ---- derived images (first 3 photos)
            progress("images")
            src_bytes: dict[int, bytes] = {}
            need = sorted(set(photos_changed) | ({0, 1} if thumb_changed else set()))
            def get_src(i):
                kind, v = src_ref[i]
                return i, (v if kind == "new" else repo.read_blob(v))
            with ThreadPoolExecutor(3) as ex:
                src_bytes.update(dict(ex.map(get_src, need)))
            app_files: dict[str, bytes] = {}
            if photos_changed or thumb_changed:
                derived = {}
                for i in need:
                    data = src_bytes[i]
                    w720 = images.webp_width(data, 720)
                    derived[f"{i + 1:02d}-720.webp"] = w720
                    if i in (0, 1):
                        derived[f"{i + 1:02d}-480.webp"] = images.webp_width(data, 480)
                for name, data in derived.items():
                    if name[:2] in ("01", "02"):
                        files[f"{THUMBS}/{pid}/{name}"] = data
                    if name in ("01-480.webp", "01-720.webp", "02-720.webp", "03-720.webp"):
                        app_files[f"img/{pid}/{name}"] = data
                if 0 in need:
                    files[f"{PRICE_THUMBS}/{pid}.jpg"] = images.price_thumb(src_bytes[0])

            # ---- Telegram (new post needs ids before the commit; edits go after it)
            queue = self._queue(repo)
            caption_changed = (not old) or any(old.get(k) != prod.get(k) for k in CAPTION_KEYS)
            rec = (posts.get("posts") or {}).get(pid)
            tg_action = None
            jobs: set[str] = set()
            if rec:
                jobs |= {f"photo{i + 1}" for i in photos_changed if i < len(rec)}
                if caption_changed:
                    jobs.add("caption")
                jobs |= set((queue["items"].get(pid) or {}).get("what") or [])
                jobs.discard("post")
            need_post = not rec and new_msg_ids is None
            if (need_post or jobs) and tg_ok is None:
                progress("telegram")
                tg_ok = tg.ping()
            if need_post and tg_ok:
                jpgs = [images.tg_jpeg(src_bytes[i] if i in src_bytes else repo.read_blob(src_ref[i][1])) for i in range(3)]
                try:
                    mids = tg.send_album(jpgs, c.build_caption(prod, None))
                    url = f"https://t.me/{c.CHANNEL}/{mids[0]}"
                    new_msg_ids = mids
                    tg_action = "posted"
                    try:
                        tg.edit_caption(mids[0], c.build_caption(prod, url))
                    except TgError:
                        jobs.add("caption")
                except TgError as e:
                    report["warnings"].append(f"Пост в канал не опубликован: {e}")
                    tg_ok = False
            if new_msg_ids:
                posts.setdefault("posts", {})[pid] = new_msg_ids
                tg_action = tg_action or "posted"
            if tg_ok:
                if pid in queue["items"]:
                    queue["items"].pop(pid)
                    files[TG_QUEUE] = dumps_pretty(queue)
            elif need_post or jobs:
                what = ["post"] if (need_post and not new_msg_ids) else sorted(jobs)
                self._queue_add(queue, {pid: what}, "Telegram недоступен с сервера")
                files[TG_QUEUE] = dumps_pretty(queue)
                tg_action = "queued"

            # ---- PDF
            progress("pdf")
            thumb_paths = [f"{PRICE_THUMBS}/{p['id']}.jpg" for p in products
                           if f"{PRICE_THUMBS}/{p['id']}.jpg" not in files]
            have = repo.read_many(thumb_paths)
            missing = [p for p in products if f"{PRICE_THUMBS}/{p['id']}.jpg" not in files and not have.get(f"{PRICE_THUMBS}/{p['id']}.jpg")]
            for p in missing:  # no stored thumbnail yet -> make it from photo 01
                sha = repo.tree.get("public" + p["images"][0]) if p.get("images") else None
                if sha:
                    files[f"{PRICE_THUMBS}/{p['id']}.jpg"] = images.price_thumb(repo.read_blob(sha))
            def thumb(p):
                v = files.get(f"{PRICE_THUMBS}/{p['id']}.jpg")
                return v if isinstance(v, bytes) else have.get(f"{PRICE_THUMBS}/{p['id']}.jpg")
            files[PDF] = pdfgen.build_pdf(products, cats_new, thumb)

            # ---- Mini App + data
            catalog_json = appcat.dumps(appcat.build(products, cats_new, posts))
            files[f"{SITE_APP}/data/catalog.json"] = catalog_json
            for path, data in app_files.items():
                files[f"{SITE_APP}/{path}"] = data
            files[PRODUCTS] = dumps_pretty(products)
            files[CATEGORIES] = dumps_pretty(cats_new)
            files[TG_POSTS] = dumps_pretty(posts)

            progress("commit")
            verb = "изменена" if old else "добавлена"
            try:
                res = repo.commit(files, f"Админка: модель {prod['article']} {verb}")
            except GitHubError as e:
                last_err = e
                if e.status in (409, 422) and attempt < 2:
                    time.sleep(1.5)
                    continue
                if new_msg_ids and not tg.dry_run:
                    try:
                        tg.delete(new_msg_ids)
                        report["warnings"].append("Пост в канале отменён, потому что сайт не сохранился")
                    except TgError:
                        report["warnings"].append(f"Сайт не сохранился, а пост в канале остался: {new_msg_ids}")
                raise
            report["steps"].append({"step": "site", "ok": True, "commit": res})
            break
        else:
            raise last_err or GitHubError("не удалось сохранить")

        # ---- Telegram edits for an existing post (after the site is saved)
        if rec and not new_msg_ids and tg_ok and jobs:
            def img(_p, i):
                if i in src_bytes:
                    return src_bytes[i]
                kind, v = src_ref[i]
                return v if kind == "new" else repo.read_blob(v)
            failed, done, _ = self._tg_run(tg, {pid: jobs}, {pid: prod}, posts, img, time.time() + 100)
            if failed:
                tg_action = "queued"
                report["warnings"].append("Пост в канале не обновился, Telegram недоступен. Изменение поставлено в очередь.")
                self._queue_commit(failed)
            else:
                tg_action = ("edited: " + ", ".join(done.get(pid, []))) if done.get(pid) else "unchanged"
        elif rec and not jobs:
            tg_action = "unchanged"
        if tg_action == "queued" and not any("очеред" in w for w in report["warnings"]):
            report["warnings"].append("Telegram сейчас недоступен с сервера. Пост обновится, когда очередь будет отправлена.")
        report["steps"].append({"step": "telegram", "action": tg_action, "dry_run": tg.dry_run,
                                "post": appcat.post_url(posts, pid), "calls": tg.log})

        # ---- Mini App repo
        app = self.app()
        if app:
            progress("app")
            try:
                app_res = app.commit({"data/catalog.json": catalog_json, **app_files},
                                     f"Админка: модель {prod['article']} {verb}")
                report["steps"].append({"step": "app", "ok": True, "commit": app_res})
            except GitHubError as e:
                report["warnings"].append(f"Mini App (отдельный репозиторий) не обновился: {e}")
        report.update(id=pid, product=prod, head=res.get("sha"), seconds=round(time.time() - t0, 1),
                      pdfBytes=len(files[PDF]))
        return report

    # -- delete -----------------------------------------------------------
    def delete(self, payload: dict) -> dict:
        pid = payload.get("id")
        drop_post = bool(payload.get("deletePost"))
        report = {"steps": [], "warnings": []}
        tg = self.tg()
        for attempt in range(3):
            repo = self.site()
            repo.load_head()
            products, cats, posts = self._state(repo)
            old = next((p for p in products if p["id"] == pid), None)
            if not old:
                raise UserError("Модель уже удалена, обновите список")
            products = [p for p in products if p["id"] != pid]
            cats_new = c.recount_categories(cats, products)
            files: dict[str, object] = {}
            for prefix in (f"public/images/products/{pid}/", f"{THUMBS}/{pid}/", f"{SITE_APP}/img/{pid}/"):
                for path in repo.tree:
                    if path.startswith(prefix):
                        files[path] = None
            files[f"{PRICE_THUMBS}/{pid}.jpg"] = None
            rec = (posts.get("posts") or {}).pop(pid, None)
            if rec and not drop_post:
                posts.setdefault("removed", {})[pid] = rec
            have = repo.read_many([f"{PRICE_THUMBS}/{p['id']}.jpg" for p in products])
            files[PDF] = pdfgen.build_pdf(products, cats_new, lambda p: have.get(f"{PRICE_THUMBS}/{p['id']}.jpg"))
            catalog_json = appcat.dumps(appcat.build(products, cats_new, posts))
            files[f"{SITE_APP}/data/catalog.json"] = catalog_json
            files[PRODUCTS] = dumps_pretty(products)
            files[CATEGORIES] = dumps_pretty(cats_new)
            files[TG_POSTS] = dumps_pretty(posts)
            try:
                res = repo.commit(files, f"Админка: модель {old.get('article')} удалена")
                break
            except GitHubError as e:
                if e.status in (409, 422) and attempt < 2:
                    time.sleep(1.5)
                    continue
                raise
        report["steps"].append({"step": "site", "ok": True, "commit": res})
        tg_action = "kept"
        if rec and drop_post:
            try:
                tg.delete(rec)
                tg_action = "deleted"
            except TgError as e:
                tg_action = "queued"
                report["warnings"].append(f"Пост в канале не удалился ({e}), удаление поставлено в очередь.")
                self._queue_commit({pid: {"what": ["delete"], "reason": str(e), "mids": rec}})
        report["steps"].append({"step": "telegram", "action": tg_action, "dry_run": tg.dry_run, "calls": tg.log})
        app = self.app()
        if app:
            try:
                app.load_head()
                app_files = {p: None for p in app.tree if p.startswith(f"img/{pid}/")}
                app_files["data/catalog.json"] = catalog_json
                report["steps"].append({"step": "app", "ok": True,
                                        "commit": app.commit(app_files, f"Админка: модель {old.get('article')} удалена")})
            except GitHubError as e:
                report["warnings"].append(f"Mini App (отдельный репозиторий) не обновился: {e}")
        report.update(id=pid, head=res.get("sha"))
        return report

    # -- Telegram queue ------------------------------------------------------
    # api.telegram.org is filtered from Yandex Cloud, so failed channel updates are kept in
    # data/tg-queue.json (same commit) and sent later by /tg-retry or tools/admin-api/flush_tg_queue.py.
    def _queue(self, repo: Repo) -> dict:
        q = repo.read_json(TG_QUEUE, default={"version": 1, "items": {}})
        q.setdefault("items", {})
        return q

    @staticmethod
    def _queue_add(queue: dict, jobs: dict, reason: str, mids: dict | None = None, articles: dict | None = None) -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        for pid, what in jobs.items():
            item = queue["items"].get(pid) or {"what": [], "since": now}
            what = set(item.get("what") or []) | set(what)
            if "delete" in what:
                what = {"delete"}
            elif "post" in what:
                what = {"post"}
            item.update(what=sorted(what), reason=reason, at=now)
            if mids and mids.get(pid):
                item["mids"] = mids[pid]
            if articles and articles.get(pid):
                item["article"] = articles[pid]
            queue["items"][pid] = item

    def _queue_commit(self, failed: dict, cleared: tuple = ()) -> None:
        """Follow-up commit for updates that failed after the main commit."""
        for attempt in range(3):
            repo = self.site()
            repo.load_head()
            q = self._queue(repo)
            for pid in cleared:
                q["items"].pop(pid, None)
            for pid, f in failed.items():
                self._queue_add(q, {pid: f["what"]}, f["reason"], {pid: f.get("mids")})
            try:
                repo.commit({TG_QUEUE: dumps_pretty(q)}, "Канал: очередь обновлений постов")
                return
            except GitHubError as e:
                if e.status in (409, 422) and attempt < 2:
                    time.sleep(1.5)
                    continue
                print("queue commit failed:", e)
                return

    def _tg_run(self, tg: Telegram, jobs: dict, by_id: dict, posts: dict, img, deadline: float,
                mids_for: dict | None = None):
        """Run channel updates. jobs: pid -> set of caption|photo1..3|post|delete.
        Returns (failed {pid: {what, reason, mids}}, done {pid: [labels]}, posts_changed)."""
        failed, done, posts_changed = {}, {}, False
        down = None
        names = {"caption": "подпись", "photo1": "фото 1", "photo2": "фото 2", "photo3": "фото 3",
                 "post": "новый пост", "delete": "пост удалён"}
        for pid, what in jobs.items():
            what = set(what)
            mids = (mids_for or {}).get(pid)
            if down or time.time() > deadline:
                failed[pid] = {"what": sorted(what), "reason": down or "не хватило времени, остальное в очереди",
                               "mids": mids}
                continue
            try:
                if "delete" in what:
                    if mids:
                        tg.delete(mids)
                    done[pid] = [names["delete"]]
                    continue
                p = by_id.get(pid)
                if not p:
                    continue
                rec = (posts.get("posts") or {}).get(pid)
                if "post" in what or not rec:
                    if len(p.get("images") or []) < 3:
                        continue
                    jpgs = [images.tg_jpeg(img(p, i)) for i in range(3)]
                    new = tg.send_album(jpgs, c.build_caption(p, None))
                    posts.setdefault("posts", {})[pid] = new
                    posts_changed = True
                    tg.edit_caption(new[0], c.build_caption(p, f"https://t.me/{c.CHANNEL}/{new[0]}"))
                    done[pid] = [names["post"]]
                    continue
                cap = c.build_caption(p, f"https://t.me/{c.CHANNEL}/{rec[0]}")
                did = []
                for i in range(3):
                    if f"photo{i + 1}" in what and i < len(rec) and i < len(p.get("images") or []):
                        tg.edit_photo(rec[i], images.tg_jpeg(img(p, i)), cap if i == 0 else None)
                        did.append(names[f"photo{i + 1}"])
                        if not tg.dry_run:
                            time.sleep(TG_PAUSE)
                if "caption" in what and "photo1" not in what:
                    tg.edit_caption(rec[0], cap)
                    did.append(names["caption"])
                    if not tg.dry_run:
                        time.sleep(TG_PAUSE)
                done[pid] = did
            except TgError as e:
                if "недоступен" in str(e):
                    down = str(e)
                failed[pid] = {"what": sorted(what), "reason": str(e), "mids": mids}
        return failed, done, posts_changed

    def tg_retry(self) -> dict:
        t0 = time.time()
        repo = self.site()
        repo.load_head()
        products, cats, posts = self._state(repo)
        queue = self._queue(repo)
        if not queue["items"]:
            return {"ok": True, "sent": 0, "left": 0}
        tg = self.tg()
        if not tg.ping():
            return {"ok": False, "sent": 0, "left": len(queue["items"]),
                    "error": "Telegram по-прежнему недоступен с сервера"}
        by_id = {p["id"]: p for p in products}
        jobs = {pid: set(v.get("what") or []) for pid, v in queue["items"].items()}
        mids = {pid: v.get("mids") for pid, v in queue["items"].items()}
        img = lambda p, i: repo.read("public" + p["images"][i])  # noqa: E731
        failed, done, posts_changed = self._tg_run(tg, jobs, by_id, posts, img, t0 + 120, mids)
        for pid in list(queue["items"]):
            if pid not in failed:
                queue["items"].pop(pid)
        for pid, f in failed.items():
            self._queue_add(queue, {pid: f["what"]}, f["reason"], {pid: f.get("mids")})
        files = {TG_QUEUE: dumps_pretty(queue)}
        catalog_json = None
        if posts_changed:
            files[TG_POSTS] = dumps_pretty(posts)
            catalog_json = appcat.dumps(appcat.build(products, cats, posts))
            files[f"{SITE_APP}/data/catalog.json"] = catalog_json
        res = repo.commit(files, "Канал: отправлены отложенные обновления постов")
        app = self.app()
        if app and catalog_json:
            try:
                app.commit({"data/catalog.json": catalog_json}, "Канал: новые посты")
            except GitHubError as e:
                print("app commit failed:", e)
        return {"ok": not failed, "sent": len(done), "left": len(failed), "head": res.get("sha"),
                "done": done, "dry_run": tg.dry_run}

    # -- files for download -------------------------------------------------
    def pdf(self, sha: str = "") -> dict:
        repo = self.site()
        ref = sha if re.fullmatch(r"[0-9a-f]{7,40}", sha or "") else self.cfg["SITE_BRANCH"]
        r = repo._req("GET", f"/contents/{PDF}?ref={ref}", headers={"Accept": "application/vnd.github.raw+json"})
        return {"filename": "ESLAVIA-optovyy-prays.pdf", "data": base64.b64encode(r.content).decode(),
                "bytes": len(r.content)}

    def export(self) -> dict:
        repo = self.site()
        head = repo.load_head()
        products, cats, posts = self._state(repo)
        names = [x["name"] for x in cats] or c.CATEGORIES
        for n in c.CATEGORIES:
            if n not in names:
                names.append(n)
        data = xlsx.export(products, names, posts, self.cfg["IMAGE_BASE"])
        return {"filename": f"ESLAVIA-katalog-{time.strftime('%Y-%m-%d')}.xlsx",
                "data": base64.b64encode(data).decode(), "head": head, "count": len(products)}

    # -- Excel import -------------------------------------------------------
    @staticmethod
    def _table_bytes(payload: dict) -> bytes:
        raw = payload.get("data") or ""
        if "," in raw[:80]:
            raw = raw.split(",", 1)[1]
        try:
            data = base64.b64decode(raw)
        except Exception:  # noqa: BLE001
            raise UserError("Файл не прочитался, загрузите его ещё раз")
        if not data:
            raise UserError("Пустой файл")
        if len(data) > 2_500_000:
            raise UserError("Файл слишком большой")
        return data

    def _diff(self, repo: Repo, payload: dict):
        products, cats, posts = self._state(repo)
        names = c.category_order(cats)
        try:
            d = xlsx.diff(self._table_bytes(payload), products, names)
        except xlsx.TableError as e:
            raise UserError(str(e))
        return d, products, cats, posts

    @staticmethod
    def _signature(d: dict) -> str:
        sig = {"c": [(x["id"], x["values"]) for x in d["changes"]], "a": [x["values"] for x in d["added"]],
               "m": [x["id"] for x in d["missing"]], "o": d.get("order")}
        return hashlib.sha1(json.dumps(sig, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def import_preview(self, payload: dict) -> dict:
        repo = self.site()
        head = repo.load_head()
        d, *_ = self._diff(repo, payload)
        d.update(head=head, signature=self._signature(d))
        for x in d["changes"] + d["added"]:
            x.pop("values", None)
        return d

    def import_apply(self, payload: dict) -> dict:
        t0 = time.time()
        report = {"steps": [], "warnings": []}
        tg = self.tg()
        tg_ok = None
        for attempt in range(3):
            repo = self.site()
            repo.load_head()
            d, products, cats, posts = self._diff(repo, payload)
            if d["errors"]:
                raise UserError(f"В таблице есть ошибки ({len(d['errors'])}), проверьте её ещё раз")
            if payload.get("signature") and payload["signature"] != self._signature(d):
                raise UserError("Каталог изменился после проверки таблицы. Загрузите таблицу ещё раз и проверьте изменения")
            dels = d["missing"]
            if dels and int(payload.get("confirmDelete") or 0) != len(dels):
                raise UserError(f"Подтвердите удаление {len(dels)} мод.")
            if not (d["changes"] or d["added"] or dels):
                return {"unchanged": True, "steps": [], "warnings": []}
            del_ids = {x["id"] for x in dels}
            index = {p["id"]: i for i, p in enumerate(products)}
            by_id = {p["id"]: dict(p) for p in products}
            queue = self._queue(repo)
            files: dict[str, object] = {}
            cap_jobs: dict[str, set] = {}
            for ch in d["changes"]:
                p = by_id[ch["id"]]
                before = dict(p)
                v = ch["values"]
                for k, val in v.items():
                    if k in ("order", "extraCategories"):
                        continue
                    else:
                        p[k] = val
                cat = p.get("category")
                if "extraCategories" in v:
                    p["categories"] = [cat] + [x for x in v["extraCategories"] if x != cat]
                elif "category" in v:
                    old_list = before.get("categories") or [before.get("category")]
                    p["categories"] = [cat] + [x for x in old_list if x not in (before.get("category"), cat)]
                if not p.get("material") and before.get("material") is None:
                    p["material"] = None
                if any(before.get(k) != p.get(k) for k in CAPTION_KEYS) and (posts.get("posts") or {}).get(p["id"]):
                    cap_jobs[p["id"]] = {"caption"}
                by_id[p["id"]] = p
            if d.get("order"):
                seq = [i for i in d["order"] if i not in del_ids]
                rest = [p["id"] for p in products if p["id"] not in del_ids and p["id"] not in set(seq)]
                new_list = [by_id[i] for i in seq + rest]
            else:
                new_list = [by_id[p["id"]] for p in products if p["id"] not in del_ids]
            for a in d["added"]:
                v = a["values"]
                cat = v["category"]
                prod = {"id": a["id"], "article": v["article"], "name": v["name"], "category": cat,
                        "categories": [cat] + [x for x in v.get("extraCategories") or [] if x != cat],
                        "priceRetail": float(v["priceRetail"]), "priceWholesale": float(v["priceWholesale"]),
                        "sizes": v["sizes"], "colors": v.get("colors") or [], "material": v.get("material") or None,
                        "description": v.get("description") or "", "availability": v.get("availability") or "Есть в наличии",
                        "images": [], "sourceUrl": v.get("sourceUrl") or ""}
                if v.get("order"):
                    new_list.insert(max(0, min(len(new_list), int(v["order"]) - 1)), prod)
                    continue
                idx = max([i for i, p in enumerate(new_list) if p.get("category") == cat], default=len(new_list) - 1)
                new_list.insert(idx + 1, prod)
            products_new = new_list
            cats_new = c.recount_categories(cats, products_new)

            # deletions: files + posts, as in /delete with deletePost
            del_jobs, del_mids = {}, {}
            for pid in del_ids:
                for prefix in (f"public/images/products/{pid}/", f"{THUMBS}/{pid}/", f"{SITE_APP}/img/{pid}/"):
                    for path in repo.tree:
                        if path.startswith(prefix):
                            files[path] = None
                files[f"{PRICE_THUMBS}/{pid}.jpg"] = None
                rec = (posts.get("posts") or {}).pop(pid, None)
                queue["items"].pop(pid, None)
                if rec:
                    del_jobs[pid] = {"delete"}
                    del_mids[pid] = rec
            jobs = {**cap_jobs, **del_jobs}
            if jobs and tg_ok is None:
                tg_ok = tg.ping()
            if jobs and not tg_ok:
                self._queue_add(queue, cap_jobs, "Telegram недоступен с сервера")
                self._queue_add(queue, del_jobs, "Telegram недоступен с сервера", del_mids,
                                {x["id"]: x["article"] for x in dels})
            elif jobs:
                for pid in cap_jobs:
                    queue["items"].pop(pid, None)
            files[TG_QUEUE] = dumps_pretty(queue)

            # PDF
            have = repo.read_many([f"{PRICE_THUMBS}/{p['id']}.jpg" for p in products_new if p.get("images")])
            for p in products_new:
                k = f"{PRICE_THUMBS}/{p['id']}.jpg"
                if p.get("images") and not have.get(k):
                    sha = repo.tree.get("public" + p["images"][0])
                    if sha:
                        files[k] = images.price_thumb(repo.read_blob(sha))
            def thumb(p):
                v = files.get(f"{PRICE_THUMBS}/{p['id']}.jpg")
                return v if isinstance(v, bytes) else have.get(f"{PRICE_THUMBS}/{p['id']}.jpg")
            files[PDF] = pdfgen.build_pdf(products_new, cats_new, thumb)
            catalog_json = appcat.dumps(appcat.build(products_new, cats_new, posts))
            files[f"{SITE_APP}/data/catalog.json"] = catalog_json
            files[PRODUCTS] = dumps_pretty(products_new)
            files[CATEGORIES] = dumps_pretty(cats_new)
            files[TG_POSTS] = dumps_pretty(posts)
            parts = []
            if d["changes"]:
                parts.append(f"изменено {len(d['changes'])}")
            if d["added"]:
                parts.append(f"добавлено {len(d['added'])}")
            if dels:
                parts.append(f"удалено {len(dels)}")
            msg = "Админка: таблица каталога, " + ", ".join(parts)
            try:
                res = repo.commit(files, msg)
                break
            except GitHubError as e:
                if e.status in (409, 422) and attempt < 2:
                    time.sleep(1.5)
                    continue
                raise
        report["steps"].append({"step": "site", "ok": True, "commit": res})

        tg_action = "unchanged"
        done: dict = {}
        if jobs and tg_ok:
            img = lambda p, i: repo.read_blob(repo.tree["public" + p["images"][i]])  # noqa: E731
            failed, done, _ = self._tg_run(tg, jobs, {p["id"]: p for p in products_new}, posts, img,
                                           t0 + 130, del_mids)
            if failed:
                self._queue_commit(failed)
                tg_action = "queued"
                report["warnings"].append(f"Не все посты в канале обновились ({len(failed)}), они поставлены в очередь.")
            else:
                tg_action = f"edited: {len(done)} пост." if done else "unchanged"
        elif jobs:
            tg_action = "queued"
            report["warnings"].append(f"Telegram сейчас недоступен с сервера. Посты ({len(jobs)}) обновятся, "
                                      "когда очередь будет отправлена.")
        report["steps"].append({"step": "telegram", "action": tg_action, "dry_run": tg.dry_run,
                                "jobs": len(jobs), "done": len(done), "calls": tg.log[:50]})
        app = self.app()
        if app:
            try:
                app.load_head()
                app_files: dict[str, object] = {"data/catalog.json": catalog_json}
                for pid in del_ids:
                    for path in app.tree:
                        if path.startswith(f"img/{pid}/"):
                            app_files[path] = None
                report["steps"].append({"step": "app", "ok": True, "commit": app.commit(app_files, msg)})
            except GitHubError as e:
                report["warnings"].append(f"Mini App (отдельный репозиторий) не обновился: {e}")
        if d["added"]:
            report["warnings"].append("Новые модели добавлены без фото: " + ", ".join(a["article"] for a in d["added"])
                                      + ". Добавьте фото в их карточках, тогда появятся посты в канале.")
        report.update(head=res.get("sha"), seconds=round(time.time() - t0, 1), pdfBytes=len(files[PDF]),
                      counts={"changed": len(d["changes"]), "added": len(d["added"]), "deleted": len(dels)})
        return report
