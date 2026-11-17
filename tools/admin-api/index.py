"""Yandex Cloud Function: ESLAVIA admin API (behind API Gateway, routes by path)."""
from __future__ import annotations

import base64
import json
import os
import re
import time
import traceback

from core import auth
from core.gh import GitHubError
from core.pipeline import Pipeline, UserError

THROTTLE = auth.Throttle()


def _flag(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _secret(name: str) -> str | None:
    v = (os.environ.get(name) or "").strip()
    return None if not v or v.upper().startswith("PLACEHOLDER") else v


def config() -> dict:
    return {
        "SITE_REPO": os.environ.get("SITE_REPO", "Paulos99/eslavia-admin-test"),
        "SITE_BRANCH": os.environ.get("SITE_BRANCH", "main"),
        "APP_REPO": os.environ.get("APP_REPO", ""),
        "APP_BRANCH": os.environ.get("APP_BRANCH", "main"),
        "GITHUB_TOKEN": _secret("GITHUB_TOKEN"),
        "GITHUB_DRY_RUN": _flag("GITHUB_DRY_RUN", "0"),
        "TG_TOKEN": _secret("TG_TOKEN"),
        "TG_CHAT_ID": os.environ.get("TG_CHAT_ID", "-1004469691410"),
        "TG_DRY_RUN": _flag("TG_DRY_RUN", "1"),
        "IMAGE_BASE": os.environ.get("IMAGE_BASE", "https://eslavia.ru"),
    }


def _origin_ok(origin: str) -> bool:
    allowed = [o for o in re.split(r"[,; ]+", os.environ.get("ALLOWED_ORIGINS", "https://eslavia.ru")) if o]
    return origin in allowed


def _resp(status: int, body: dict, origin: str = "") -> dict:
    headers = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
               "X-Content-Type-Options": "nosniff", "Vary": "Origin"}
    if origin and _origin_ok(origin):
        headers.update({"Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Headers": "Authorization, Content-Type",
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Max-Age": "600"})
    return {"statusCode": status, "headers": headers, "isBase64Encoded": False,
            "body": json.dumps(body, ensure_ascii=False)}


def handler(event, context=None):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    origin = headers.get("origin", "")
    method = (event.get("httpMethod") or "GET").upper()
    path = (event.get("url") or event.get("path") or "/").split("?", 1)[0]
    path = "/" + path.strip("/").split("/", 1)[-1] if path.startswith("/api/") else path.rstrip("/") or "/"
    if method == "OPTIONS":
        return _resp(204 if _origin_ok(origin) else 403, {}, origin)
    if origin and not _origin_ok(origin):
        return _resp(403, {"error": "Доступ с этого сайта запрещён"}, origin)
    ip = ((event.get("requestContext") or {}).get("identity") or {}).get("sourceIp") or headers.get("x-forwarded-for", "?")
    try:
        body = {}
        if event.get("body"):
            raw = event["body"]
            if event.get("isBase64Encoded"):
                raw = base64.b64decode(raw).decode("utf-8")
            body = json.loads(raw)
        if path == "/health":
            cfg = config()
            return _resp(200, {"ok": True, "repo": cfg["SITE_REPO"], "githubDryRun": cfg["GITHUB_DRY_RUN"],
                               "telegramDryRun": cfg["TG_DRY_RUN"]}, origin)
        if path == "/login" and method == "POST":
            wait = THROTTLE.blocked(ip)
            if wait:
                return _resp(429, {"error": f"Слишком много попыток. Попробуйте через {max(1, wait // 60)} мин."}, origin)
            if not auth.verify_password(str(body.get("password", "")), auth.env_secret("ADMIN_PASSWORD_HASH")):
                THROTTLE.fail(ip)
                time.sleep(1.0)
                return _resp(401, {"error": "Неверный пароль"}, origin)
            THROTTLE.ok(ip)
            token, exp = auth.issue_token(auth.env_secret("SESSION_SECRET"), int(os.environ.get("SESSION_TTL", "43200")))
            return _resp(200, {"token": token, "exp": exp}, origin)

        bearer = headers.get("authorization", "")
        token = bearer[7:] if bearer.lower().startswith("bearer ") else None
        if not auth.check_token(auth.env_secret("SESSION_SECRET"), token):
            return _resp(401, {"error": "Сессия закончилась, войдите снова"}, origin)
        pipe = Pipeline(config())
        if path == "/products" and method == "GET":
            return _resp(200, pipe.listing(), origin)
        if path == "/save" and method == "POST":
            return _resp(200, pipe.save(body), origin)
        if path == "/delete" and method == "POST":
            return _resp(200, pipe.delete(body), origin)
        if path == "/status" and method == "GET":
            qs = event.get("queryStringParameters") or {}
            return _resp(200, pipe.status(qs.get("sha", "")), origin)
        return _resp(404, {"error": "Нет такого адреса"}, origin)
    except UserError as e:
        return _resp(400, {"error": str(e)}, origin)
    except GitHubError as e:
        print("github error:", e)
        return _resp(502, {"error": f"Не удалось сохранить на сайт: {e}"}, origin)
    except Exception as e:  # noqa: BLE001
        print("internal error:", e.__class__.__name__, traceback.format_exc()[-1500:])
        return _resp(500, {"error": "Внутренняя ошибка, изменения не сохранены"}, origin)
