from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, IPvAnyAddress


class CreateModem(BaseModel):
    """
    Class represents fields for creating modem.
    """

    ip: IPvAnyAddress
    port: int = Field(lt=65536, gt=49152)
    bind_user_email: EmailStr | None = None
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)


class ShowModem(BaseModel):
    """
    Class represents fields for displaying a modem.
    """

    id: int
    ip: IPvAnyAddress
    port: int
    hashed_value: str | None
    bind_user_email: str | None
    username: str | None
    password: str | None
    rebooted: datetime | None
    created: datetime
    updated: datetime | None


class UpdateModem(BaseModel):
    """
    Class represents fields for updating a modem.
    """

    ip: IPvAnyAddress
    bind_user_email: EmailStr | None = None
    port: int | None = Field(lt=65536, gt=49152, default=None)
    username: str | None = None
    password: str | None = None
    rebooted: datetime | None = None


class ShowModemForUser(BaseModel):
    """
    Class represents modem info for displaying modem info for a user.
    """

    ip: IPvAnyAddress
    port: int
    hashed_value: str | None
    rebooted: datetime | None
    created: datetime | None
