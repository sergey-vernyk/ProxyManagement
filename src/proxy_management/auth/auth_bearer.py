from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from ..config import get_settings

settings = get_settings()


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Returns generated access JWT."""
    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc) + expires_delta
        if expires_delta is not None
        else datetime.now(timezone.utc) + timedelta(minutes=15)
    )

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, key=settings.secret_key, algorithm=settings.algorithm)
