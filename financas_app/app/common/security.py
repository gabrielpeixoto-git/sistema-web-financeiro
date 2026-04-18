from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from financas_app.app.settings import get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

ALGO = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(payload: dict[str, Any], *, expires_in: timedelta) -> str:
    exp = _now() + expires_in
    data = {**payload, "exp": exp}
    return jwt.encode(data, get_settings().secret_key, algorithm=ALGO)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=[ALGO])
    except JWTError as e:
        raise ValueError("invalid token") from e


def new_refresh_id() -> str:
    return str(uuid.uuid4())


def refresh_cookie_token() -> str:
    # opaque token stored only in cookie; DB stores sha256(token)
    return uuid.uuid4().hex + uuid.uuid4().hex


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def make_access_token(*, user_id: int) -> str:
    mins = get_settings().access_token_expire_minutes
    return _encode({"sub": str(user_id), "typ": "access"}, expires_in=timedelta(minutes=mins))


def make_refresh_jwt(*, user_id: int, refresh_id: str) -> str:
    days = get_settings().refresh_token_expire_days
    return _encode(
        {"sub": str(user_id), "typ": "refresh", "rid": refresh_id},
        expires_in=timedelta(days=days),
    )


def is_dev() -> bool:
    return os.getenv("APP_ENV", "dev") == "dev"

