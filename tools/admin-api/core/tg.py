"""Telegram Bot API calls for the channel posts. Dry-run mode records payloads instead of sending."""
from __future__ import annotations

import itertools
import json
import time

import requests

_fake_ids = itertools.count(int(time.time()) % 100000 * 10 + 900000)


class TgError(Exception):
    pass


class Telegram:
    def __init__(self, token: str | None, chat_id: str, dry_run: bool = True, simulate_down: bool = False):
        self.token, self.chat_id, self.dry_run = token, chat_id, dry_run
        self.simulate_down = simulate_down
        self.log: list[dict] = []
        if not dry_run and not token:
            raise TgError("нет токена бота")

    def _call(self, method: str, data: dict, files: dict | None = None):
        entry = {"method": method, "data": {k: v for k, v in data.items()}}
        if files:
            entry["files"] = {k: f"{len(v[1])} bytes JPEG" for k, v in files.items()}
        self.log.append(entry)
        if self.dry_run:
            if method == "sendMediaGroup":
                n = len(json.loads(data["media"]))
                return [{"message_id": next(_fake_ids)} for _ in range(n)]
            return True
        if self.simulate_down:
            raise TgError("Telegram недоступен (тест)")
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        conn_fails = 0
        for attempt in range(4):
            try:
                r = requests.post(url, data=data, files=files, timeout=(6, 90))
                j = r.json()
            except (requests.ConnectionError, requests.Timeout) as e:
                # api.telegram.org is filtered from Yandex Cloud: don't burn the whole timeout on retries
                conn_fails += 1
                if conn_fails >= 2 or attempt == 3:
                    raise TgError(f"Telegram недоступен ({e.__class__.__name__})")
                time.sleep(1)
                continue
            except (requests.RequestException, ValueError) as e:
                if attempt == 3:
                    raise TgError(f"Telegram недоступен ({e.__class__.__name__})")
                time.sleep(2 + attempt * 3)
                continue
            if j.get("ok"):
                return j["result"]
            desc = j.get("description", "")
            if "message is not modified" in desc:
                return True
            retry = (j.get("parameters") or {}).get("retry_after")
            if retry and attempt < 3:
                time.sleep(min(int(retry), 30) + 1)
                continue
            raise TgError(f"Telegram: {desc}")
        raise TgError("Telegram: нет ответа")

    def ping(self) -> bool:
        """Quick reachability check (getMe) before a commit, so failed edits can be queued in the same commit."""
        if self.dry_run:
            return not self.simulate_down
        if self.simulate_down:
            return False
        try:
            r = requests.get(f"https://api.telegram.org/bot{self.token}/getMe", timeout=(5, 10))
            return bool(r.json().get("ok"))
        except (requests.RequestException, ValueError):
            try:
                r = requests.get(f"https://api.telegram.org/bot{self.token}/getMe", timeout=(5, 10))
                return bool(r.json().get("ok"))
            except (requests.RequestException, ValueError):
                return False

    def send_album(self, jpegs: list[bytes], caption: str) -> list[int]:
        media, files = [], {}
        for n, data in enumerate(jpegs):
            item = {"type": "photo", "media": f"attach://photo{n}"}
            if n == 0:
                item.update(caption=caption, parse_mode="HTML")
            media.append(item)
            files[f"photo{n}"] = (f"photo{n}.jpg", data, "image/jpeg")
        res = self._call("sendMediaGroup", {"chat_id": self.chat_id,
                                            "media": json.dumps(media, ensure_ascii=False)}, files)
        return [m["message_id"] for m in res]

    def edit_caption(self, message_id: int, caption: str) -> None:
        self._call("editMessageCaption", {"chat_id": self.chat_id, "message_id": message_id,
                                          "caption": caption, "parse_mode": "HTML"})

    def edit_photo(self, message_id: int, jpeg: bytes, caption: str | None) -> None:
        media = {"type": "photo", "media": "attach://photo"}
        if caption is not None:
            media.update(caption=caption, parse_mode="HTML")
        self._call("editMessageMedia", {"chat_id": self.chat_id, "message_id": message_id,
                                        "media": json.dumps(media, ensure_ascii=False)},
                   {"photo": ("photo.jpg", jpeg, "image/jpeg")})

    def send_text(self, text: str, keyboard: dict | None = None) -> int:
        data = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML", "disable_notification": "true",
                "link_preview_options": json.dumps({"is_disabled": True})}
        if keyboard:
            data["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
        res = self._call("sendMessage", data)
        return res["message_id"] if isinstance(res, dict) else next(_fake_ids)

    def edit_text(self, message_id: int, text: str, keyboard: dict | None = None) -> None:
        data = {"chat_id": self.chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML",
                "link_preview_options": json.dumps({"is_disabled": True})}
        if keyboard:
            data["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
        self._call("editMessageText", data)

    def blank_photo(self, message_id: int, jpeg: bytes | None = None, file_id: str | None = None) -> str | None:
        """Replace a photo with the placeholder; no caption, no buttons. Returns the file_id for reuse."""
        media = {"type": "photo", "media": file_id or "attach://photo"}
        files = None if file_id else {"photo": ("blank.jpg", jpeg, "image/jpeg")}
        res = self._call("editMessageMedia", {"chat_id": self.chat_id, "message_id": message_id,
                                              "media": json.dumps(media)}, files)
        if isinstance(res, dict) and res.get("photo"):
            return res["photo"][-1]["file_id"]
        return file_id

    def clear_caption(self, message_id: int) -> None:
        self._call("editMessageCaption", {"chat_id": self.chat_id, "message_id": message_id, "caption": ""})

    def unpin(self, message_id: int) -> None:
        self._call("unpinChatMessage", {"chat_id": self.chat_id, "message_id": message_id})

    def pin(self, message_id: int) -> None:
        self._call("pinChatMessage", {"chat_id": self.chat_id, "message_id": message_id, "disable_notification": "true"})

    def delete(self, message_ids: list[int]) -> None:
        self._call("deleteMessages", {"chat_id": self.chat_id, "message_ids": json.dumps(message_ids)})
