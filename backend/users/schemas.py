from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field

from modems.schemas import ShowModemForUser


class UserRole(str, Enum):
    """Users roles in the system."""

    ADMIN = "admin"
    REGULAR = "regular"


class HashType(str, Enum):
    """Type of the hash for a password."""

    MD5 = "md5"
    SHA256 = "sha256"


class UserBase(BaseModel):
    """Base class for user."""

    email: EmailStr = Field(examples=["example@example.com"], description="Email address of the user.")
    password: str = Field(min_length=10, max_length=30, examples=["strongspassword"])


class CreateRegularUser(UserBase):
    """Class represents fields for creating a regular user."""

    proxy_password_plain: str = Field(
        min_length=10,
        max_length=30,
        examples=["proxypassword"],
        description="Login for accessing a proxy.",
    )
    proxy_password_hash_type: HashType | None = Field(
        description="Hash type for a proxy password for using in proxy config.",
        default=None,
    )
    role: UserRole = Field(default=UserRole.REGULAR)


class CreateAdminUser(UserBase):
    """Class represents fields for creating an admin user."""

    password: str = Field(min_length=10, max_length=30)
    role: UserRole = Field(default=UserRole.ADMIN)


class ShowUser(BaseModel):
    """Class represents fields for displaying a user."""

    id: int
    email: str
    role: UserRole
    is_verified: bool = Field(description="Flag, which defines whether a user verified their email.")
    hashed_password: str
    token: str | None = Field(description="Unique user token. Creates automatically during user creation.")
    proxy_login: str | None = Field(description="Password for accessing a proxy.")
    proxy_password_plain: str | None = Field(description="Login for accessing a proxy.")
    proxy_password_hashed: str | None = Field(description="Hashed password for a proxy used in config file.")
    proxy_password_hash_type: str | None
    created: datetime
    updated: datetime | None
    user_modems: list[ShowModemForUser] = Field(description="List of modems binds to a user.")


class UpdateUser(BaseModel):
    """
    Class represents fields for updating a user.
    """

    email: EmailStr | None = None
    update_password: bool = Field(
        description="Flag for indicating a user intention to update their password.",
        default=False,
    )
    old_password: str | None = Field(
        max_length=30,
        min_length=10,
        default=None,
        description="Old user password. Must be used with the flag 'update_password'.",
    )
    new_password: str | None = Field(
        max_length=30,
        min_length=10,
        default=None,
        description="New user password. Must be used with the flag 'update_password'.",
    )
    update_token: bool = Field(
        description="Flag for indicating a user intention to update their token.",
        default=False,
    )

    update_proxy_login: bool = Field(
        description="Flag for indicating a user intention to update their proxy login. Generates automatically.",
        default=False,
    )
    update_proxy_password: bool = Field(
        description="Flag for indicating a user intention to update their proxy password.",
        default=False,
    )
    proxy_password_plain: str | None = Field(
        description="New proxy password. Must used with the flag 'update_proxy_password'.",
        default=None,
    )
    proxy_password_hash_type: HashType | None = None
