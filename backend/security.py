import hashlib

import bcrypt
from config import get_settings

settings = get_settings()

ENCODING = settings.default_encoding


def encrypt_modem_password(hash_type: str, plain_password: str) -> str:
    """
    Encrypts and returns the given `plain_password` with `hash_type`.
    """
    hash_func = getattr(hashlib, hash_type)
    return hash_func(plain_password.encode(ENCODING)).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check whether `plain_password` against an `hashed_password`.
    """
    return bcrypt.checkpw(plain_password.encode(ENCODING), hashed_password.encode(ENCODING))


def get_password_hash(password: str) -> str:
    """
    Returns hash from the passed plain `password`.
    """
    return bcrypt.hashpw(password.encode(ENCODING), bcrypt.gensalt()).decode(ENCODING)
