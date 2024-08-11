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


class CreateAdminUser(BaseModel):
    """
    Class represents fields for creating an admin user.
    """

    email: EmailStr
    role: UserRole = Field(default=UserRole(UserRole.ADMIN))
    password: str = Field(min_length=10, max_length=30)


class CreateRegularUser(BaseModel):
    """
    Class represents fields for creating a regular user.
    """

    email: EmailStr
    password: str = Field(min_length=10, max_length=30)
    role: UserRole = Field(default=UserRole(UserRole.REGULAR))
    proxy_password: str = Field(min_length=10, max_length=30)
    proxy_password_hash_type: HashType | None = None


class ShowRegularUser(BaseModel):
    """
    Class represents fields for displaying a regular user.
    """

    id: int
    email: str
    hashed_password: str
    token: str
    proxy_login: str
    proxy_password: str
    created: datetime
    updated: datetime | None
    user_modems: list[ShowModemForUser]


class ShowAdminUser(BaseModel):
    """
    Class represents fields for displaying a n admin user.
    """

    id: int
    email: str
    hashed_password: str
    created: datetime
    updated: datetime | None


class UpdateUserProxyCredentials(BaseModel):
    """
    Class for defining proxy credentials fields for updating.
    """

    update_login: bool = False
    proxy_password: str | None = Field(min_length=10, max_length=30, default=None)
    proxy_password_hash_type: HashType


class UpdateRegularUser(BaseModel):
    """
    Class represents fields for updating a regular user.
    """

    email: EmailStr
