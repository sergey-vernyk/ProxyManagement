from datetime import datetime
from enum import Enum

from modems.schemas import ShowModemForUser
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """
    Users roles in the system.
    """

    ADMIN = "admin"
    REGULAR = "regular"


class HashType(str, Enum):
    """
    Type of the hash for a password.
    """

    MD5 = "md5"
    SHA256 = "sha256"


class UserBase(BaseModel):
    """
    Base class for user.
    """

    email: EmailStr
    password: str = Field(min_length=10, max_length=30)
    role: UserRole


class CreateRegularUser(UserBase):
    """
    Class represents fields for creating a regular user.
    """

    proxy_password: str = Field(min_length=10, max_length=30)
    proxy_password_hash_type: HashType | None = None
    role: UserRole = Field(default=UserRole(UserRole.REGULAR))


class CreateAdminUser(UserBase):
    """
    Class represents fields for creating an admin user.
    """

    email: EmailStr
    password: str = Field(min_length=10, max_length=30)
    role: UserRole = Field(default=UserRole(UserRole.ADMIN))


class ShowUser(BaseModel):
    """
    Class represents fields for displaying a user.
    """

    id: int
    email: str
    role: str
    hashed_password: str
    token: str | None
    proxy_login: str | None
    proxy_password: str | None
    created: datetime
    updated: datetime | None
    user_modems: list[ShowModemForUser]


class UpdateUserProxyCredentials(BaseModel):
    """
    Class for defining proxy credentials fields for updating.
    """

    update_login: bool = False
    proxy_password: str | None = Field(min_length=10, max_length=30, default=None)
    proxy_password_hash_type: HashType


class UpdateUser(BaseModel):
    """
    Class represents fields for updating a user.
    """

    email: EmailStr
