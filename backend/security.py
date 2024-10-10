import hashlib
import random
from string import digits

import bcrypt
from config import get_settings
from fastapi.security import OAuth2AuthorizationCodeBearer
from passlib.hash import md5_crypt

settings = get_settings()

ENCODING: str = settings.default_encoding


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    scheme_name="GitHub OAuth",
    authorizationUrl="https://github.com/login/oauth/authorize",
    tokenUrl="https://github.com/login/oauth/access_token",
    scopes={"read:user": "Read info about a users."},
)


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


def generate_random_otp(length: int = 8) -> str:
    """
    Generates random one-time password (OTP).

    Args:
        length (int, optional): length of the generated plain code. Defaults to 8.

    Returns:
        str: random plain otp.
    """
    return "".join(random.sample(digits, length))


def generate_hashed_otp(plain_code: str) -> str:
    """
    Generate hashed OTP from provided `plain_code`.

    Args:
        plain_code (str): string for generating hash.

    Returns:
        str: hash value.
    """
    return hashlib.sha256(plain_code.encode(ENCODING)).hexdigest()
