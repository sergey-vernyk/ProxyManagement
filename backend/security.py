import hashlib

import bcrypt
from config import get_settings
from passlib.hash import md5_crypt

settings = get_settings()

ENCODING: str = settings.default_encoding


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


def generate_md5_crypt_hash_password(password: str, salt: bool = False) -> str:
    """
    Generate and return the given `password` into md5-crypt hash.
    If `salt` is True the salt will be generated and added to the hashed password.
    """
    passwd_salt = None

    if salt:
        passwd_salt = bcrypt.gensalt()

    return md5_crypt.hash(password, salt=passwd_salt)
