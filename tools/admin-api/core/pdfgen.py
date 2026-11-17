"""Wholesale price PDF in the current design (A4, grid 5 columns, 180x240 thumbnails).

Geometry is taken 1:1 from the approved file optovyy-prays-actual.pdf (ReportLab, top-down
coordinates below are converted to ReportLab's bottom-up ones in _y()).
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .catalog import category_order, fmt_price, natural_key

HERE = Path(__file__).resolve().parents[1]
FONTS = HERE / "fonts"
LOGO = HERE / "assets" / "logo.png"
SITE = "https://eslavia.ru"

PAGE_W, PAGE_H = A4
MM = 72 / 25.4
LEFT, RIGHT = 10 * MM, PAGE_W - 10 * MM          # 28.35 .. 566.93
CONTENT_TOP = 26 * MM                              # 73.70: first row / heading on pages 2+
BOTTOM_LIMIT = 273 * MM                            # rows must end above this (footer rule at 275 mm)

C_BG, C_BAND, C_BRAND = HexColor("#f7f1ea"), HexColor("#e8d4ce"), HexColor("#60413d")
C_TEXT, C_MUTED, C_LINE = HexColor("#3a2e2a"), HexColor("#8a6a62"), HexColor("#d4c4bc")
C_BOX, C_CARD = HexColor("#efe6dc"), HexColor("#fffcf9")

COLS = 5
CARD_W = 102.7276
COL_STEP = 108.9646
CARD_H = 170.2874
ROW_STEP = CARD_H + 2 * MM
INSET = 1.2 * MM
IMG_BOX_H = 129.0445
BTN_W, BTN_H = 50.34, 12.57
RADIUS = 2.5

# PDF groups: heading -> categories shown under it (in this order)
GROUPS = [("Платья", ["Платья", "Сарафаны", "Туники"]),
          ("Пижамы для дома", ["Пижамы для дома"]),
          ("Сорочки", ["Сорочки"]),
          ("Халаты", ["Халаты"])]

LEGAL = "Эславия · ИП Шлыкова А.Г. · ИНН 370202329400 · ОГРНИП 323370000044608"
CONTACT = "+7 (901) 694-01-48  ·  Eslaviya.37@yandex.ru"
PICKUP = "Самовывоз: г. Иваново, ул. Ташкентская, д. 20 · г. Кохма, ул. Ивановская, 17 (ТЦ Кохомский)"
SUB1 = "Женский трикотаж · комфорт натуральных тканей на каждый день"
SUB2 = "Цены при заказе от 5 000 ₽  ·  размеры 42–72  ·  самовывоз Иваново / Кохма"
INTRO = ("Мы выпускаем продукцию для женщин и девушек, которые ценят комфорт натуральных тканей и стремятся "
         "в домашней обстановке и на отдыхе выглядеть ярко и красиво. Широкий размерный ряд — от 42 до 72.")
BOX_TITLE = "Оптовые цены по артикулам"
CONDITIONS = ("Актуальные условия подтвердим при заказе · самовывоз Иваново / Кохма · "
              "срок пошива 2–3 недели · индивидуальный пошив")
HOWTO = ["Оставьте заявку на сайте или напишите нам — подтвердим условия и поможем с подбором.",
         "Телефон: +7 (901) 694-01-48  ·  Eslaviya.37@yandex.ru",
         "ИП Шлыкова А.Г. · ИНН 370202329400 · ОГРНИП 323370000044608",
         "Самовывоз: г. Иваново, ул. Ташкентская, д. 20",
         "г. Кохма, ул. Ивановская, 17 (ТЦ Кохомский)",
         "Срок пошива 2–3 недели · Индивидуальный пошив"]

_fonts_ready = False


def _fonts() -> None:
    global _fonts_ready
    if _fonts_ready:
        return
    pdfmetrics.registerFont(TTFont("DejaVuSans", str(FONTS / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(FONTS / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("CormorantGaramond-Light", str(FONTS / "CormorantGaramond-Light.ttf")))
    _fonts_ready = True


def _y(top_down: float) -> float:
    return PAGE_H - top_down


def group_products(products: list[dict], categories_json: list | None) -> list[tuple[str, list[dict]]]:
    order = category_order(categories_json)
    groups = [(h, list(cats)) for h, cats in GROUPS]
    known = {c for _, cats in groups for c in cats}
    for c in order + sorted({p.get("category") or "" for p in products}):
        if c and c not in known:
            groups.append((c, [c]))
            known.add(c)
    out = []
    for heading, cats in groups:
        items = []
        for cat in cats:
            items += sorted([p for p in products if p.get("category") == cat],
                            key=lambda p: natural_key(p.get("article") or p["id"]))
        if items:
            out.append((heading, items))
    return out


def build_pdf(products: list[dict], categories_json: list | None,
              thumb: Callable[[dict], bytes | None]) -> bytes:
    """thumb(product) -> JPEG bytes 180x240 (or None for an empty frame)."""
    _fonts()
    groups = group_products(products, categories_json)
    # pass 1: layout -> list of pages, each a list of ops
    pages: list[list[tuple]] = [[]]
    y = None  # current top-down cursor (bottom of last placed element)

    def new_page():
        pages.append([])

    # page 1 header occupies up to 209.48 (box bottom)
    first_heading_baseline = 209.4803 + 5.5 * MM
    for gi, (heading, items) in enumerate(groups):
        # heading position
        if gi == 0:
            hb = first_heading_baseline
        else:
            hb = y + 3.5 * MM
            if hb + 7.5 * MM + CARD_H > BOTTOM_LIMIT:
                new_page()
                hb = CONTENT_TOP
        pages[-1].append(("heading", heading, hb))
        row_top = hb + 7.5 * MM
        for r in range(0, len(items), COLS):
            if row_top + CARD_H > BOTTOM_LIMIT:
                new_page()
                row_top = CONTENT_TOP
            for c, p in enumerate(items[r:r + COLS]):
                pages[-1].append(("card", p, LEFT + c * COL_STEP, row_top))
            y = row_top + CARD_H
            row_top += ROW_STEP
    box_top = (y or CONTENT_TOP) + 1.5 * MM
    box_h = 36 * MM
    if box_top + box_h > BOTTOM_LIMIT:
        new_page()
        box_top = CONTENT_TOP
    pages[-1].append(("howto", box_top, box_h))

    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4, pageCompression=1)
    cv.setTitle("ЭСЛАВИЯ — оптовый прайс")
    cv.setAuthor("ЭСЛАВИЯ")
    total = len(pages)
    for n, ops in enumerate(pages, 1):
        _page_frame(cv, n, total)
        for op in ops:
            if op[0] == "heading":
                _heading(cv, op[1], op[2])
            elif op[0] == "card":
                _card(cv, op[1], op[2], op[3], thumb)
            elif op[0] == "howto":
                _howto(cv, op[1], op[2])
        cv.showPage()
    cv.save()
    return buf.getvalue()


def _center(cv, text, font, size, color, baseline, cx=PAGE_W / 2):
    cv.setFont(font, size)
    cv.setFillColor(color)
    cv.drawCentredString(cx, _y(baseline), text)


def _page_frame(cv, n: int, total: int) -> None:
    cv.setFillColor(C_BG)
    cv.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    cv.setFillColor(C_BAND)
    cv.rect(0, _y(7 * MM), PAGE_W, 7 * MM, stroke=0, fill=1)
    if n == 1:
        logo_h = 19 * MM
        logo_w = logo_h * 900 / 261
        cv.drawImage(ImageReader(str(LOGO)), PAGE_W / 2 - logo_w / 2, _y(15 * MM + logo_h), logo_w, logo_h, mask="auto")
        _center(cv, "Оптовый прайс", "CormorantGaramond-Light", 24, C_BRAND, 110.55)
        _center(cv, SUB1, "DejaVuSans", 8.5, C_MUTED, 126.14)
        _center(cv, SUB2, "DejaVuSans", 8.0, C_MUTED, 138.05)
        cv.setStrokeColor(C_BRAND)
        cv.setLineWidth(0.7)
        oy = _y(147.97)
        cv.line(20 * MM, oy, PAGE_W / 2 - 4 * MM, oy)
        cv.line(PAGE_W / 2 + 4 * MM, oy, 190 * MM, oy)
        cv.setFillColor(C_BRAND)
        cv.circle(PAGE_W / 2, oy, 1.1, stroke=0, fill=1)
        lines = simpleSplit(INTRO, "DejaVuSans", 8, RIGHT - LEFT)
        for i, line in enumerate(lines):
            _center(cv, line, "DejaVuSans", 8, C_TEXT, 164.98 + i * 10.2)
        cv.setFillColor(C_BOX)
        cv.roundRect(LEFT, _y(209.4803), RIGHT - LEFT, 209.4803 - 182.5511, RADIUS, stroke=0, fill=1)
        _center(cv, BOX_TITLE, "DejaVuSans-Bold", 7.5, C_BRAND, 193.04)
        _center(cv, CONDITIONS, "DejaVuSans", 7.0, C_MUTED, 203.33)
    else:
        cv.setFont("CormorantGaramond-Light", 15)
        cv.setFillColor(C_BRAND)
        cv.drawString(LEFT, _y(48.19), "Эславия · оптовый прайс")
        cv.setStrokeColor(C_LINE)
        cv.setLineWidth(0.7)
        cv.line(LEFT, _y(20 * MM), RIGHT, _y(20 * MM))
    # footer
    cv.setStrokeColor(C_LINE)
    cv.setLineWidth(0.6)
    cv.line(LEFT, _y(275 * MM), RIGHT, _y(275 * MM))
    cv.setFillColor(C_MUTED)
    cv.setFont("DejaVuSans", 7.2)
    cv.drawString(LEFT, _y(792.28), LEGAL)
    cv.drawRightString(RIGHT, _y(792.28), f"{n} / {total}")
    cv.setFont("DejaVuSans", 7.0)
    cv.drawString(LEFT, _y(803.62), CONTACT)
    cv.setFont("DejaVuSans", 6.5)
    cv.drawString(LEFT, _y(813.54), PICKUP)


def _heading(cv, text: str, baseline: float) -> None:
    cv.setFont("CormorantGaramond-Light", 14)
    cv.setFillColor(C_BRAND)
    cv.drawString(LEFT, _y(baseline), text)
    cv.setStrokeColor(C_BAND)
    cv.setLineWidth(2)
    cv.line(LEFT, _y(baseline + 3 * MM), LEFT + 26 * MM, _y(baseline + 3 * MM))


def _card(cv, p: dict, x: float, top: float, thumb) -> None:
    url = f"{SITE}/?product={p['id']}"
    cv.setFillColor(C_CARD)
    cv.setStrokeColor(C_LINE)
    cv.setLineWidth(0.55)
    cv.roundRect(x, _y(top + CARD_H), CARD_W, CARD_H, RADIUS, stroke=1, fill=1)
    ix, itop, iw = x + INSET, top + INSET, CARD_W - 2 * INSET
    cv.setFillColor(white)
    cv.setLineWidth(0.35)
    cv.rect(ix, _y(itop + IMG_BOX_H), iw, IMG_BOX_H, stroke=1, fill=1)
    data = thumb(p)
    if data:
        ih = iw * 4 / 3
        off = (IMG_BOX_H - ih) / 2
        cv.drawImage(ImageReader(io.BytesIO(data)), ix, _y(itop + off + ih), iw, ih)
    cv.linkURL(url, (ix, _y(itop + IMG_BOX_H), ix + iw, _y(itop)), relative=0)
    cx = x + CARD_W / 2
    _center(cv, p.get("article") or "", "DejaVuSans", 7, C_TEXT, top + 142.28, cx)
    _center(cv, f"{fmt_price(p['priceWholesale'])} ₽", "DejaVuSans-Bold", 7.5, C_BRAND, top + 152.05, cx)
    bx, btop = cx - BTN_W / 2, top + 154.88
    cv.setFillColor(C_BRAND)
    cv.roundRect(bx, _y(btop + BTN_H), BTN_W, BTN_H, BTN_H / 2, stroke=0, fill=1)
    _center(cv, "В каталог →", "DejaVuSans", 6.5, white, top + 164.17, cx)
    cv.linkURL(url, (bx, _y(btop + BTN_H), bx + BTN_W, _y(btop)), relative=0)


def _howto(cv, top: float, h: float) -> None:
    cv.setFillColor(C_BOX)
    cv.roundRect(LEFT, _y(top + h), RIGHT - LEFT, h, RADIUS, stroke=0, fill=1)
    _center(cv, "Как заказать", "CormorantGaramond-Light", 12, C_BRAND, top + 7.5 * MM)
    for i, line in enumerate(HOWTO):
        _center(cv, line, "DejaVuSans", 7.5, C_TEXT, top + 34.01 + i * 3.5 * MM)


def thumb_from_image_bytes(data: bytes) -> bytes:
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB").resize((180, 240), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=80, optimize=True)
        return out.getvalue()
