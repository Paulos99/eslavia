"""Save / delete a product: site repo (one commit) + price PDF + Mini App + Telegram."""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

from . import appcat, catalog as c, images, pdfgen
from .gh import GitHubError, Repo
from .tg import Telegram, TgError

PRODUCTS = "data/products.json"
CATEGORIES = "data/categories.json"
TG_POSTS = "data/tg-posts.json"
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
        return Telegram(self.cfg.get("TG_TOKEN"), self.cfg["TG_CHAT_ID"], dry_run=self.cfg["TG_DRY_RUN"])

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
        return {"products": products, "categories": [x["name"] for x in cats] or c.CATEGORIES,
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

            # ---- Telegram (new post needs ids before the commit)
            caption_changed = (not old) or any(old.get(k) != prod.get(k) for k in ("name", "article", "sizes", "priceWholesale", "category"))
            rec = (posts.get("posts") or {}).get(pid)
            tg_action = None
            if not rec and new_msg_ids is None:
                progress("telegram")
                jpgs = [images.tg_jpeg(src_bytes[i] if i in src_bytes else repo.read_blob(src_ref[i][1])) for i in range(3)]
                try:
                    mids = tg.send_album(jpgs, c.build_caption(prod, None))
                    url = f"https://t.me/{c.CHANNEL}/{mids[0]}"
                    tg.edit_caption(mids[0], c.build_caption(prod, url))
                    new_msg_ids = mids
                    tg_action = "posted"
                except TgError as e:
                    report["warnings"].append(f"Пост в канал не опубликован: {e}")
                    tg_action = "failed"
            if new_msg_ids:
                posts.setdefault("posts", {})[pid] = new_msg_ids
                tg_action = tg_action or "posted"

            # ---- PDF
            progress("pdf")
            thumb_paths = [f"{PRICE_THUMBS}/{p['id']}.jpg" for p in products
                           if f"{PRICE_THUMBS}/{p['id']}.jpg" not in files]
            have = repo.read_many(thumb_paths)
            missing = [p for p in products if f"{PRICE_THUMBS}/{p['id']}.jpg" not in files and not have.get(f"{PRICE_THUMBS}/{p['id']}.jpg")]
            for p in missing:  # no stored thumbnail yet -> make it from photo 01
                sha = repo.tree.get("public" + p["images"][0])
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
        if rec and not new_msg_ids:
            try:
                url = f"https://t.me/{c.CHANNEL}/{rec[0]}"
                cap = c.build_caption(prod, url)
                did = []
                for i in photos_changed:
                    if i < len(rec):
                        tg.edit_photo(rec[i], images.tg_jpeg(src_bytes[i]), cap if i == 0 else None)
                        did.append(f"фото {i + 1}")
                if caption_changed and 0 not in photos_changed:
                    tg.edit_caption(rec[0], cap)
                    did.append("подпись")
                tg_action = ("edited: " + ", ".join(did)) if did else "unchanged"
            except TgError as e:
                tg_action = "failed"
                report["warnings"].append(f"Пост в канале не обновился: {e}")
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
                tg_action = "failed"
                report["warnings"].append(f"Пост в канале не удалился: {e}")
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
