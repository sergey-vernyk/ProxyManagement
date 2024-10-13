from datetime import datetime, timedelta, timezone
from typing import Any

from config import get_settings
from jose import jwt

settings = get_settings()


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Returns generated jwt access token.
    """
    to_encode = data.copy()
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, key=settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt
