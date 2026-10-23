"""Login/Register: password hash (PBKDF2) + JWT (HS256), kono extra library lage na. User MongoDB 'users' collection-e thake."""
import base64
import hashlib
import hmac
import json
import os
import time

from .config import settings


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False


def create_token(sub: str, role: str, ttl_days: int = 7) -> str:
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps({"sub": sub, "role": role, "exp": int(time.time()) + ttl_days * 86400}).encode())
    sig = hmac.new(settings.JWT_SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{_b64(sig)}"


def decode_token(token: str):
    try:
        head, body, sig = token.split(".")
        calc = hmac.new(settings.JWT_SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64(calc), sig):
            return None
        payload = json.loads(_unb64(body))
        return payload if payload.get("exp", 0) > time.time() else None
    except Exception:
        return None
