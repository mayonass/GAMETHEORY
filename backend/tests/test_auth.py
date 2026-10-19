"""Přihlášení s "Stay logged in" vydá token s delší platností."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-tests-0123456789")

import jwt

from app.config import get_settings
from app.security import create_access_token, decode_access_token


def _dni_platnosti(token: str) -> float:
    s = get_settings()
    exp = jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm])["exp"]
    return (exp - datetime.now(timezone.utc).timestamp()) / 86400


def test_bezny_token_plati_den_dlouhy_30_dni():
    uid = uuid.uuid4()
    assert 0.99 < _dni_platnosti(create_access_token(uid)) <= 1.0
    dlouhy = create_access_token(uid, remember=True)
    assert 29.99 < _dni_platnosti(dlouhy) <= 30.0
    assert decode_access_token(dlouhy) == uid
