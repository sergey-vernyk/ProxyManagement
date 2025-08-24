import hashlib
import random
import secrets
from string import digits

import bcrypt
from passlib.hash import md5_crypt

from proxy_management.config import get_settings

settings = get_settings()

ENCODING: str = settings.default_encoding


def encrypt_modem_password(hash_type: str, plain_password: str) -> str:
    """Encrypts and returns the given `plain_password` with `hash_type`."""
    hash_func = getattr(hashlib, hash_type)
    return hash_func(plain_password.encode(ENCODING)).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check whether `plain_password` against an `hashed_password`."""
    return bcrypt.checkpw(plain_password.encode(ENCODING), hashed_password.encode(ENCODING))


def get_password_hash(password: str) -> str:
    """Returns hash from the passed plain `password`."""
    return bcrypt.hashpw(password.encode(ENCODING), bcrypt.gensalt()).decode(ENCODING)


def generate_md5_crypt_hash_password(password: str, salt: bool = False) -> str:
    """
    Generate and return the given `password` into md5-crypt hash.
    If `salt` is True the salt will be generated and added to the hashed password.
    """
    passwd_salt = None

    if salt:
        passwd_salt = bcrypt.gensalt()

    return md5_crypt.hash(password, salt=passwd_salt)


def generate_random_plain_otp(length: int = 8) -> str:
    """Generates random not encrypted one-time password (OTP)."""
    return "".join(random.sample(digits, length))


def generate_hashed_otp(plain_code: str) -> str:
    """Generate hashed OTP from provided `plain_code`."""
    return hashlib.sha256(plain_code.encode(ENCODING)).hexdigest()


def generate_csrf_token(n_bytes: int | None = None) -> str:
    """Generates a CSRF token consisting of `n_bytes` random bytes, encoded in a URL-safe format."""
    return secrets.token_urlsafe(n_bytes)
