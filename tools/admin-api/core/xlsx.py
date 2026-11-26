"""Catalog <-> Excel: export the whole catalog, parse an edited table and diff it against products.json."""
from __future__ import annotations

import io
import re
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import catalog as c

AVAILABILITY = ["Есть в наличии", "Под заказ", "Нет в наличии"]
SHEET = "Каталог"
MAX_ROWS = 2000

# key, header, width, editable, help
COLUMNS = [
    ("id", "Код модели", 14, False, "Служебный код, по нему строка связана с моделью. Не меняйте. У новой модели оставьте пустым."),
    ("article", "Артикул", 13, True, "Обязательно. Должен быть уникальным."),
    ("name", "Название", 34, True, "Обязательно. Так модель подписана на сайте, в прайсе и в канале."),
    ("category", "Категория", 18, True, "Обязательно. Если категории нет в списке, впишите её: кабинет спросит, добавлять ли её."),
    ("extraCategories", "Доп. категории", 18, True, "Если модель должна показываться ещё в других разделах. Через «;»."),
    ("priceWholesale", "Опт, ₽", 10, True, "Обязательно. Цена в прайсе, в канале и в Mini App."),
    ("priceRetail", "Розница, ₽", 11, True, "Обязательно. Цена на сайте."),
    ("sizes", "Размеры", 26, True, "Обязательно. Через «;» или «,»: 46-48; 50-52 или 48; 50; 52."),
    ("colors", "Цвета", 24, True, "Через запятую."),
    ("material", "Материал", 14, True, "Например, хлопок."),
    ("availability", "Наличие", 16, True, "Выбор из списка."),
    ("description", "Описание", 60, True, "Текст карточки на сайте."),
    ("sourceUrl", "Ссылка на WB", 30, True, "Ссылка на карточку на Wildberries, можно оставить пустой."),
    ("order", "Порядок на сайте", 11, True, "Номер места в каталоге сайта. Чтобы переставить модель, поменяйте номер."),
    ("photoCount", "Фото, шт", 9, False, "Только для сведения. Фото меняются в карточке модели в кабинете."),
    ("photos", "Фото (адреса)", 46, False, "Только для сведения."),
    ("post", "Пост в канале", 30, False, "Только для сведения."),
]
LABEL = {k: h for k, h, *_ in COLUMNS}
EDITABLE = [k for k, _, _, e, _ in COLUMNS if e]
# headers of the older hand-made table are understood too
ALIASES = {"id": "id", "код": "id", "код модели": "id", "артикул": "article", "название": "name",
           "категория": "category", "доп. категории": "extraCategories", "доп категории": "extraCategories",
           "опт, ₽": "priceWholesale", "цена_опт_₽": "priceWholesale", "опт": "priceWholesale", "цена опт": "priceWholesale",
           "розница, ₽": "priceRetail", "цена_розница_₽": "priceRetail", "розница": "priceRetail", "цена розница": "priceRetail",
           "размеры": "sizes", "цвета": "colors", "цвет": "colors", "материал": "material", "наличие": "availability",
           "описание": "description", "ссылка на wb": "sourceUrl", "ссылка_wb": "sourceUrl", "ссылка wb": "sourceUrl",
           "порядок на сайте": "order", "порядок": "order", "фото, шт": "photoCount", "фото (адреса)": "photos",
           "пост в канале": "post"}

HEAD_FILL = PatternFill("solid", fgColor="2B2622")
RO_HEAD_FILL = PatternFill("solid", fgColor="8A817A")
RO_FILL = PatternFill("solid", fgColor="EFEBE7")
THIN = Side(style="thin", color="DDD6CF")


def _ws(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _num_text(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _price_cell(v):
    f = float(v or 0)
    return int(f) if f.is_integer() else f


# ---------------------------------------------------------------- export
def export(products: list[dict], categories: list[str], posts: dict, image_base: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.append([h for _, h, *_ in COLUMNS])
    for idx, p in enumerate(products, 1):
        mids = (posts.get("posts") or {}).get(p["id"])
        extra = [x for x in (p.get("categories") or []) if x != p.get("category")]
        imgs = p.get("images") or []
        row = {
            "id": p["id"], "article": p.get("article") or "", "name": p.get("name") or "",
            "category": p.get("category") or "", "extraCategories": "; ".join(extra),
            "priceWholesale": _price_cell(p.get("priceWholesale")), "priceRetail": _price_cell(p.get("priceRetail")),
            "sizes": "; ".join(str(s) for s in p.get("sizes") or []), "colors": ", ".join(p.get("colors") or []),
            "material": p.get("material") or "", "availability": p.get("availability") or "",
            "description": p.get("description") or "", "sourceUrl": p.get("sourceUrl") or "", "order": idx,
            "photoCount": len(imgs), "photos": "\n".join(image_base.rstrip("/") + x for x in imgs),
            "post": f"https://t.me/{posts.get('channel', c.CHANNEL)}/{mids[0]}" if mids else "",
        }
        ws.append([row[k] for k, *_ in COLUMNS])
    n = ws.max_row
    for col, (key, head, width, editable, help_) in enumerate(COLUMNS, 1):
        L = get_column_letter(col)
        ws.column_dimensions[L].width = width
        hc = ws.cell(1, col)
        hc.font = Font(bold=True, color="FFFFFF")
        hc.fill = HEAD_FILL if editable else RO_HEAD_FILL
        hc.alignment = Alignment(wrap_text=True, vertical="center")
        for r in range(2, n + 1):
            cell = ws.cell(r, col)
            cell.border = Border(bottom=THIN)
            wrap = key in ("description", "photos", "name", "sizes", "colors")
            cell.alignment = Alignment(wrap_text=wrap, vertical="top")
            if not editable:
                cell.fill = RO_FILL
                cell.font = Font(color="6B625B")
            if key in ("priceWholesale", "priceRetail"):
                cell.number_format = "# ##0"
            if key in ("article", "sizes", "id"):
                cell.number_format = "@"
    ws.row_dimensions[1].height = 32
    for r in range(2, n + 1):
        ws.row_dimensions[r].height = 60
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{n}"

    # lists for data validation live on a hidden sheet
    lists = wb.create_sheet("Списки")
    for i, name in enumerate(categories, 1):
        lists.cell(i, 1, name)
    for i, name in enumerate(AVAILABILITY, 1):
        lists.cell(i, 2, name)
    lists.sheet_state = "hidden"
    col_of = {k: get_column_letter(i) for i, (k, *_) in enumerate(COLUMNS, 1)}
    dv_cat = DataValidation(type="list", formula1=f"='Списки'!$A$1:$A${len(categories)}", allow_blank=False,
                            showErrorMessage=True, errorStyle="warning", errorTitle="Новая категория",
                            error="Этой категории нет в списке. Если её нужно добавить, оставьте название: кабинет спросит подтверждение.")
    dv_av = DataValidation(type="list", formula1=f"='Списки'!$B$1:$B${len(AVAILABILITY)}", allow_blank=False,
                           showErrorMessage=True, errorTitle="Наличие", error="Выберите значение из списка")
    last = max(n + 200, 300)
    dv_cat.add(f"{col_of['category']}2:{col_of['category']}{last}")
    dv_av.add(f"{col_of['availability']}2:{col_of['availability']}{last}")
    ws.add_data_validation(dv_cat)
    ws.add_data_validation(dv_av)

    # instructions first
    ins = wb.create_sheet("Как править", 0)
    ins.column_dimensions["A"].width = 24
    ins.column_dimensions["B"].width = 90
    lines = [
        ("Каталог ЭСЛАВИЯ", f"Выгрузка {datetime.now().strftime('%d.%m.%Y %H:%M')}, моделей: {len(products)}"),
        ("", ""),
        ("Как пользоваться", "1. Правьте нужные ячейки на листе «Каталог». Остальное не трогайте."),
        ("", "2. Сохраните файл в формате .xlsx и загрузите его в кабинете кнопкой «Загрузить таблицу»."),
        ("", "3. Кабинет покажет все найденные изменения. Пока вы не нажмёте «Применить», ничего не меняется."),
        ("", "4. После применения сайт, оптовый прайс, Mini App и посты в канале обновятся одним сохранением."),
        ("", ""),
        ("Серые столбцы", "Только для сведения: код модели, фото, ссылка на пост. Их правка не учитывается."),
        ("Новая категория", "Если нужного раздела нет в списке, впишите его название в столбец «Категория» "
                            "или «Доп. категории». Excel может предупредить, что значения нет в списке: "
                            "нажмите «Да». В кабинете появится вопрос, добавлять ли эту категорию."),
        ("Новая модель", "Новая строка с пустым кодом. Нужны артикул, название, категория, обе цены и размеры. "
                         "Фото и пост в канале добавляются потом в карточке модели."),
        ("Удаление", "Чтобы удалить модель, удалите её строку целиком. Перед применением кабинет покажет "
                     "список удаляемых моделей и попросит подтвердить. Модель пропадёт с сайта, из прайса, "
                     "из Mini App, её пост в канале тоже удалится."),
        ("", ""),
        ("Столбцы", ""),
    ] + [(h, ("(только для сведения) " if not e else "") + help_) for _, h, _, e, help_ in COLUMNS]
    for a, b in lines:
        ins.append([a, b])
    for r in range(1, ins.max_row + 1):
        ins.cell(r, 1).font = Font(bold=True, size=14 if r == 1 else 11)
        ins.cell(r, 1).alignment = Alignment(vertical="top")
        ins.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    wb.active = 1
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- parse
class TableError(Exception):
    pass


def _split(v, seps=r"[;,\n]") -> list[str]:
    if v is None:
        return []
    if isinstance(v, float) and not v.is_integer():
        v = str(v).replace(".", ";")  # «46,48» turned into a decimal by Excel
    return [x for x in (_ws(t) for t in re.split(seps, _num_text(v))) if x]


def _money(v):
    if v is None or str(v).strip() == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[\s\u00a0₽рРуб.]+$", "", str(v).strip()).replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        raise ValueError("нужно число")


def read_rows(data: bytes) -> list[dict]:
    try:
        wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    except Exception:  # noqa: BLE001
        raise TableError("Не получилось открыть файл. Нужна таблица Excel в формате .xlsx")
    ws = wb[SHEET] if SHEET in wb.sheetnames else None
    if ws is None:
        for name in wb.sheetnames:
            first = next(wb[name].iter_rows(min_row=1, max_row=1, values_only=True), ())
            if any(ALIASES.get(_ws(x).lower()) == "article" for x in first):
                ws = wb[name]
                break
    if ws is None:
        raise TableError("В файле нет листа «Каталог» со столбцом «Артикул»")
    it = ws.iter_rows(values_only=True)
    header = next(it, ())
    cols: dict[int, str] = {}
    for i, h in enumerate(header):
        key = ALIASES.get(_ws(h).lower())
        if key and key not in cols.values():
            cols[i] = key
    if "article" not in cols.values():
        raise TableError("Не найден столбец «Артикул» в первой строке листа")
    rows = []
    for rn, values in enumerate(it, 2):
        if rn > MAX_ROWS:
            raise TableError(f"Слишком много строк, больше {MAX_ROWS}")
        rec = {key: (values[i] if i < len(values) else None) for i, key in cols.items()}
        if all(v is None or str(v).strip() == "" for v in rec.values()):
            continue
        rec["_row"] = rn
        rows.append(rec)
    return rows, set(cols.values())


def normalize_sizes(v) -> list[str]:
    out = []
    for x in _split(v):
        x = re.sub(r"\s*[-–—]\s*", "-", x).replace(" ", "")
        out.append(x)
    return list(dict.fromkeys(out))


def _cmp_text(v) -> str:
    return _ws(v)


def diff(data: bytes, products: list[dict], categories: list[str]) -> dict:
    """Return {changes, added, missing, errors, warnings, columns, rowsRead} — nothing is written."""
    rows, present = read_rows(data)
    by_id = {p["id"]: p for p in products}
    index = {p["id"]: i for i, p in enumerate(products)}
    errors: list[dict] = []
    warnings: list[str] = []
    changes: list[dict] = []
    added: list[dict] = []
    seen_ids: set[str] = set()
    articles: dict[str, str] = {}   # lower article -> row label
    ignored = {k for k in ("photoCount", "photos", "post") if k in present}
    order_changed = False
    order_keys: dict[str, tuple] = {}

    def err(row, msg, col=None):
        errors.append({"row": row, "column": LABEL.get(col, "") if col else "", "message": msg})

    # lower name -> first spelling and the rows that use it
    fresh: dict[str, dict] = {}

    def resolve_category(raw, rn, col="category") -> str | None:
        name = _ws(raw)
        if not name:
            err(rn, "Не указана категория", col)
            return None
        if len(name) > 60:
            err(rn, "Название категории длиннее 60 знаков", col)
            return None
        hit = next((x for x in categories if x.lower() == name.lower()), None)
        if hit:
            return hit
        key = name.lower()
        rec = fresh.get(key)
        if rec:
            if rn not in rec["rows"]:
                rec["rows"].append(rn)
            return rec["name"]
        fresh[key] = {"name": name, "rows": [rn]}
        return name

    for r in rows:
        rn = r["_row"]
        rid = _ws(_num_text(r["id"])) if r.get("id") is not None else ""
        old = by_id.get(rid) if rid else None
        if rid and not old:
            # unknown code: maybe the article matches an existing model
            warnings.append(f"Строка {rn}: код «{rid}» не найден в каталоге, строка считается новой моделью")
        if old:
            if rid in seen_ids:
                err(rn, f"Модель с кодом {rid} встречается в таблице дважды", "id")
                continue
            seen_ids.add(rid)
        new: dict = {}
        row_errors = len(errors)
        for key in EDITABLE:
            if key not in present:
                continue
            v = r.get(key)
            try:
                if key in ("article", "name", "material", "sourceUrl"):
                    new[key] = _ws(_num_text(v)) if v is not None else ""
                elif key == "category":
                    got = resolve_category(v, rn)
                    if got:
                        new[key] = got
                elif key == "extraCategories":
                    lst = []
                    for x in _split(v, r"[;,\n]"):
                        got = resolve_category(x, rn, "extraCategories")
                        if got and got not in lst:
                            lst.append(got)
                    new[key] = lst
                elif key in ("priceWholesale", "priceRetail"):
                    m = _money(v)
                    if m is None:
                        err(rn, "Не указана цена", key)
                    elif not (0 < m < 1_000_000):
                        err(rn, "Цена должна быть больше нуля", key)
                    else:
                        new[key] = round(m, 2)
                elif key == "sizes":
                    sz = normalize_sizes(v)
                    bad = [x for x in sz if not re.fullmatch(r"\d{2}(-\d{2})?", x)]
                    if not sz:
                        err(rn, "Не указаны размеры", key)
                    elif bad:
                        err(rn, f"Размер «{bad[0]}» записан непонятно: нужно 52 или 50-52", key)
                    else:
                        new[key] = sz
                elif key == "colors":
                    new[key] = [x.lower() for x in _split(v, r"[;,\n]")][:20]
                elif key == "availability":
                    a = _ws(v)
                    hit = next((x for x in AVAILABILITY if x.lower() == a.lower()), None)
                    if not hit:
                        err(rn, "Наличие: выберите из списка" if a else "Не указано наличие", key)
                    else:
                        new[key] = hit
                elif key == "description":
                    new[key] = str(v).strip() if v is not None else ""
                    if len(new[key]) > 3000:
                        err(rn, "Описание длиннее 3000 знаков", key)
                elif key == "order":
                    if v is not None and str(v).strip() != "":
                        try:
                            new[key] = float(str(v).replace(",", "."))
                        except ValueError:
                            err(rn, "Порядок: нужно число", key)
            except ValueError as e:
                err(rn, str(e), key)
        if "article" in new:
            if not new["article"]:
                err(rn, "Не указан артикул", "article")
            elif len(new["article"]) > 40:
                err(rn, "Артикул слишком длинный", "article")
        if "name" in new:
            if not new["name"]:
                err(rn, "Не указано название", "name")
            elif len(new["name"]) > 120:
                err(rn, "Название слишком длинное", "name")
        if new.get("sourceUrl") and not re.match(r"https?://", new["sourceUrl"]):
            err(rn, "Ссылка должна начинаться с https://", "sourceUrl")
        for k in ("name", "description", "material"):
            if re.search(r"производ(ств|ител)", str(new.get(k) or ""), re.I):
                err(rn, "Не используем слова «производство» и «производитель»", k)
        art = (new.get("article") or (old or {}).get("article") or "").lower()
        if art:
            if art in articles:
                err(rn, f"Артикул повторяется: уже есть в строке {articles[art]}", "article")
            articles[art] = str(rn)
        if len(errors) > row_errors:
            continue

        if old:
            fields = []
            if "order" in new:
                order_keys[old["id"]] = (new["order"], rn)
            else:
                order_keys[old["id"]] = (index[old["id"]] + 1, rn)
            for key in EDITABLE:
                if key not in new or key == "order":
                    continue
                was = _old_value(old, key, index)
                now = new[key]
                if key in ("priceWholesale", "priceRetail", "order"):
                    same = float(was or 0) == float(now)
                elif key == "description":
                    same = _cmp_text(was) == _cmp_text(now)
                elif isinstance(now, list):
                    same = [str(x) for x in (was or [])] == now
                else:
                    same = _cmp_text(was) == _cmp_text(now)
                if not same:
                    if key == "order":
                        order_changed = True
                    fields.append({"field": key, "label": LABEL[key], "old": _show(key, was), "new": _show(key, now)})
            if fields:
                changes.append({"id": old["id"], "article": old.get("article"), "row": rn, "fields": fields,
                                "values": {f["field"]: new[f["field"]] for f in fields}})
        else:
            need = [k for k in ("article", "name", "category", "priceWholesale", "priceRetail", "sizes") if not new.get(k)]
            if need:
                err(rn, "Для новой модели нужны: " + ", ".join(LABEL[k].lower() for k in need))
                continue
            pid = c.product_id(new["article"])
            if not pid:
                err(rn, "Из артикула не получается адрес карточки", "article")
                continue
            if pid in by_id or any(a["id"] == pid for a in added):
                err(rn, f"Модель с артикулом {new['article']} уже есть в каталоге", "article")
                continue
            new.setdefault("availability", "Есть в наличии")
            added.append({"id": pid, "row": rn, "article": new["article"], "values": new})
            warnings.append(f"Строка {rn}: новая модель {new['article']} появится без фото. "
                            "Добавьте 3–8 фото в её карточке, тогда будет и пост в канале.")
    missing = [{"id": p["id"], "article": p.get("article"), "name": p.get("name")} for p in products if p["id"] not in seen_ids]
    # order: compare the relative order of the models in the table with the catalog, so a table
    # downloaded before other models were added/removed does not look like a mass reorder
    order_ids = None
    if "order" in present and order_keys:
        current = [p["id"] for p in products if p["id"] in order_keys]
        wanted = sorted(order_keys, key=lambda i: order_keys[i])
        if wanted != current:
            pos = {pid: i for i, pid in enumerate(current)}
            keep = set(_lis([pos[i] for i in wanted]))
            moved = [pid for pid in wanted if pos[pid] not in keep]
            by_change = {ch["id"]: ch for ch in changes}
            for pid in moved:
                old = by_id[pid]
                f = {"field": "order", "label": LABEL["order"], "old": str(current.index(pid) + 1),
                     "new": str(wanted.index(pid) + 1)}
                ch = by_change.get(pid)
                if not ch:
                    ch = {"id": pid, "article": old.get("article"), "row": order_keys[pid][1], "fields": [], "values": {}}
                    changes.append(ch)
                    by_change[pid] = ch
                ch["fields"].append(f)
                ch["values"]["order"] = wanted.index(pid) + 1
            order_ids = wanted
            order_changed = bool(moved)
    for a in added:
        if "order" in a["values"]:
            order_changed = True
    if missing and len(missing) == len(products) and products:
        raise TableError("В таблице нет ни одной модели из каталога. Похоже, загружен не тот файл")
    return {"changes": changes, "added": added, "missing": missing, "errors": errors, "warnings": warnings,
            "rowsRead": len(rows), "orderChanged": order_changed, "order": order_ids if order_changed else None,
            "columns": [LABEL[k] for k in EDITABLE if k in present],
            "unknownColumns": [],
            "newCategories": [{"name": rec["name"], "rows": rec["rows"]} for rec in fresh.values()]}


def _old_value(p: dict, key: str, index: dict):
    if key == "extraCategories":
        return [x for x in (p.get("categories") or []) if x != p.get("category")]
    if key == "order":
        return index[p["id"]] + 1
    if key in ("colors", "sizes"):
        return [str(x) for x in p.get(key) or []]
    return p.get(key)


def _show(key: str, v) -> str:
    if v is None:
        return ""
    if key in ("priceWholesale", "priceRetail"):
        return c.fmt_price(v) + " ₽"
    if key == "order":
        return _num_text(float(v))
    if isinstance(v, list):
        return "; ".join(v) if key in ("sizes", "extraCategories") else ", ".join(v)
    s = str(v)
    return s if len(s) <= 400 else s[:400] + "…"


def _lis(seq: list[int]) -> list[int]:
    """Longest increasing subsequence (values)."""
    import bisect
    tails, idx, prev = [], [], [None] * len(seq)
    for i, v in enumerate(seq):
        j = bisect.bisect_left(tails, v)
        if j == len(tails):
            tails.append(v); idx.append(i)
        else:
            tails[j] = v; idx[j] = i
        prev[i] = idx[j - 1] if j else None
    out, k = [], idx[-1] if idx else None
    while k is not None:
        out.append(seq[k]); k = prev[k]
    return out[::-1]
