# ============================================================
# Auth Service — JWT Token Generation & Password Hashing
# ============================================================

import hashlib
import hmac
import os
import time
import base64
import json
from datetime import datetime, timezone


SECRET_KEY = os.getenv("JWT_SECRET", "jobmatchr-super-secret-key-change-in-production-2026")
TOKEN_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 days


# ── Password Hashing ─────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return base64.b64encode(salt + key).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        data = base64.b64decode(hashed.encode())
        salt = data[:16]
        stored_key = data[16:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return hmac.compare_digest(key, stored_key)
    except Exception:
        return False


# ── JWT Implementation ────────────────────────────────────
# Simple, dependency-free JWT using HMAC-SHA256

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_token(user_id: str, email: str) -> str:
    """Create a JWT token."""
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps({
        "sub": user_id,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS,
    }).encode())

    signature_input = f"{header}.{payload}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
    sig = _b64url_encode(signature)

    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> dict | None:
    """Verify and decode a JWT token. Returns payload or None if invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header, payload, sig = parts
        # Verify signature
        signature_input = f"{header}.{payload}".encode()
        expected_sig = _b64url_encode(
            hmac.new(SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
        )

        if not hmac.compare_digest(sig, expected_sig):
            return None

        # Decode payload
        data = json.loads(_b64url_decode(payload))

        # Check expiry
        if data.get("exp", 0) < int(time.time()):
            return None

        return data
    except Exception:
        return None
