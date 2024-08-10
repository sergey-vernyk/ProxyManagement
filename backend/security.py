import hashlib

from config import get_settings

settings = get_settings()

ENCODING = settings.default_encoding


def encrypt_password(hash_type: str, plain_password: str) -> str:
    """
    Encrypts and returns the given `plain_password` with `hash_type`.
    """
    hash_func = getattr(hashlib, hash_type)
    return hash_func(plain_password.encode(ENCODING)).hexdigest()
