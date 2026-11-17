"""Pinned navigation post of @eslavia_opt: built from the catalog, re-posted at the bottom and pinned after updates."""
from __future__ import annotations

import hashlib
import html

from . import catalog as c

MINIAPP = "https://t.me/eslavia_opt_bot/catalog"
KEYBOARD = {"inline_keyboard": [
    [{"text": "Открыть каталог", "url": MINIAPP}],
    [{"text": "Получить оптовый прайс", "url": "http://eslavia.ru/#price-form"}],
    [{"text": "WhatsApp", "url": "https://wa.me/79016940148"}, {"text": "Telegram", "url": "https://t.me/+79016940148"}],
    [{"text": "Открыть сайт", "url": "http://eslavia.ru/"}],
]}
LABEL = {"Пижамы для дома": "Пижамы"}


def _models(n: int) -> str:
    a, b = n % 100, n % 10
    word = "моделей" if 10 < a < 20 else "модель" if b == 1 else "модели" if 1 < b < 5 else "моделей"
    return f"{n} {word}"


def build_text(products: list[dict], categories_json: list, posts: dict) -> str:
    channel = posts.get("channel") or c.CHANNEL
    mids = posts.get("posts") or {}
    lines = []
    for name in c.category_order(categories_json):
        items = [p for p in products if p.get("category") == name]
        first = [mids[p["id"]][0] for p in items if mids.get(p["id"])]
        if not items:
            continue
        label = html.escape(LABEL.get(name, name))
        link = f'<a href="https://t.me/{channel}/{min(first)}">{label}</a>' if first else label
        lines.append(f"{link} | <i>{_models(len(items))}</i>")
    return ("<b>Каталог • <i>Э С Л А В И Я</i></b>\n\n"
            "Женский трикотаж оптом и в розницу\n\n"
            "<b><i>Комфорт натуральных тканей на каждый день</i></b>\n\n"
            "Домашняя одежда, размеры 42–72\n\n"
            f"<b>Удобный <a href=\"{MINIAPP}\">оптовый каталог</a> прямо в Telegram: все модели, "
            "фильтры по категориям и размерам, заказ в один клик.</b>\n\n"
            + ("<b>Разделы канала</b>\n" + "\n".join(lines) + "\n\n" if lines else "")
            + "<b>Оптовым покупателям</b>\n"
            "• Заказ от 5 000 ₽\n"
            "• Самовывоз Иваново / Кохма\n"
            "• Срок пошива 2–3 недели\n"
            "• Индивидуальный пошив\n"
            "• Телефон для связи:\n"
            "\u00a0\u00a0\u00a0+7 (901) 694-01-48")


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def update(tg, products: list[dict], categories_json: list, posts: dict, repost: bool) -> dict:
    """repost=True: send a fresh post, pin it silently, then delete the old one (old kept if anything fails).
    repost=False: edit the text in place only if it changed. Mutates posts['navPost'/'navHash']."""
    text = build_text(products, categories_json, posts)
    h = text_hash(text)
    old = posts.get("navPost")
    if not repost and old and posts.get("navHash") == h:
        return {"action": "unchanged", "message_id": old}
    if not repost and old:
        tg.edit_text(old, text, KEYBOARD)
        posts["navHash"] = h
        return {"action": "edited", "message_id": old}
    new = tg.send_text(text, KEYBOARD)
    try:
        tg.pin(new)
    except Exception:
        try:
            tg.delete([new])
        finally:
            raise
    if old and old != new:
        try:
            tg.delete([old])
        except Exception as e:  # noqa: BLE001
            posts["navPost"], posts["navHash"] = new, h
            return {"action": "reposted", "message_id": new, "old": old, "warning": f"старый пост не удалился: {e}"}
    posts["navPost"], posts["navHash"] = new, h
    return {"action": "reposted", "message_id": new, "old": old}
