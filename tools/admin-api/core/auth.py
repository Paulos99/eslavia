from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(password: str, n: int = 2 ** 15, r: int = 8, p: int = 1) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=128 * 1024 * 1024, dklen=32)
    return f"scrypt${n}${r}${p}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p),
                              maxmem=128 * 1024 * 1024, dklen=len(_unb64(dk)))
        return hmac.compare_digest(calc, _unb64(dk))
    except (ValueError, TypeError):
        return False


def issue_token(secret: str, ttl: int) -> tuple[str, int]:
    exp = int(time.time()) + ttl
    body = _b64(json.dumps({"exp": exp, "n": secrets.token_hex(6)}, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", exp


def check_token(secret: str, token: str | None) -> bool:
    if not token or "." not in token:
        return False
    body, sig = token.rsplit(".", 1)
    good = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(good, sig):
        return False
    try:
        return json.loads(_unb64(body))["exp"] > time.time()
    except (ValueError, KeyError):
        return False


class Throttle:
    """Per-instance brute-force brake: 5 bad attempts per IP -> 15 min lock; 30 bad per instance/hour -> lock all."""

    def __init__(self):
        self.ip: dict[str, list[float]] = {}
        self.all: list[float] = []

    def blocked(self, ip: str) -> int:
        now = time.time()
        self.all = [t for t in self.all if now - t < 3600]
        bad = [t for t in self.ip.get(ip, []) if now - t < 900]
        self.ip[ip] = bad
        if len(bad) >= 5:
            return int(900 - (now - bad[0]))
        if len(self.all) >= 30:
            return int(3600 - (now - self.all[0]))
        return 0

    def fail(self, ip: str) -> None:
        now = time.time()
        self.ip.setdefault(ip, []).append(now)
        self.all.append(now)

    def ok(self, ip: str) -> None:
        self.ip.pop(ip, None)


def env_secret(name: str) -> str:
    v = os.environ.get(name, "")
    if not v:
        raise RuntimeError(f"не задан {name}")
    return v
