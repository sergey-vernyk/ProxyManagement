from datetime import datetime
from enum import Enum, auto

from modems.schemas import ShowModemForUser
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """
    Users roles in the system.
    """

    ADMIN = auto()
    REGULAR = auto()


class HashType(str, Enum):
    """
    Type of the hash for a password.
    """

    MD5 = auto()
    SHA256 = auto()


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

    proxy_password_plain: str = Field(min_length=10, max_length=30)
    proxy_password_hash_type: HashType | None = None
    role: UserRole = Field(default=UserRole.REGULAR)


class CreateAdminUser(UserBase):
    """
    Class represents fields for creating an admin user.
    """

    email: EmailStr
    password: str = Field(min_length=10, max_length=30)
    role: UserRole = Field(default=UserRole.ADMIN)


class ShowUser(BaseModel):
    """
    Class represents fields for displaying a user.
    """

    id: int
    email: str
    role: str
    is_verified: bool
    hashed_password: str
    token: str | None
    proxy_login: str | None
    proxy_password_plain: str | None
    proxy_password_hashed: str | None
    proxy_password_hash_type: str | None
    created: datetime
    updated: datetime | None
    user_modems: list[ShowModemForUser]


class UpdateUserProxyCredentials(BaseModel):
    """
    Class for defining proxy credentials fields for updating.
    """

    update_login: bool = False
    proxy_password_plain: str | None = Field(min_length=10, max_length=30, default=None)
    proxy_password_hash_type: HashType | None = None


class UpdateUser(BaseModel):
    """
    Class represents fields for updating a user.
    """

    email: EmailStr | None = None
    update_password: bool = False
    old_password: str | None = Field(max_length=30, min_length=10, default=None)
    new_password: str | None = Field(max_length=30, min_length=10, default=None)
    update_token: bool = False


class EnteredCheckOTP(BaseModel):
    """
    Class represents fields for verifying entered OTP
    along with identifying a user by the given uid and token from URL.
    """

    entered_otp: str
    uid: str
    token: str = Field(max_length=32, min_length=32)


class RecheckOTPOnDemand(BaseModel):
    """
    Class represents fields for re-checking entered OTP,
    if a user requested another one OTP when the OTP was
    expired or not correct.
    """

    uid: str
    token: str = Field(max_length=32, min_length=32)
