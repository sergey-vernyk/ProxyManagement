from enum import Enum

from modems.schemas import ShowModemForUser
from pydantic import BaseModel, EmailStr, Field


class HashType(str, Enum):
    """
    Type of the hash for a password.
    """

    MD5 = "md5"
    SHA256 = "sha256"


class CreateUser(BaseModel):
    """
    Class represents fields for creating  a user.
    """

    email: EmailStr
    password: str = Field(min_length=10, max_length=30)
    proxy_password: str = Field(min_length=10, max_length=30)
    proxy_password_hash_type: HashType | None = None


class ShowUser(BaseModel):
    """
    Class represents fields for displaying user.
    """

    id: int
    email: str
    hashed_password: str
    token: str
    proxy_login: str
    proxy_password: str
    user_modems: list[ShowModemForUser]


class UpdateUserProxyCredentials(BaseModel):
    """
    Class for defining proxy credentials fields for updating.
    """

    update_login: bool = False
    proxy_password: str | None = Field(min_length=10, max_length=30, default=None)
    proxy_password_hash_type: HashType | None = None


class UpdateUser(BaseModel):
    """
    Class represents fields for updating a user.
    """

    email: EmailStr
