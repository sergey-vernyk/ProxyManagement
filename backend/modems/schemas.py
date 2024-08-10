from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, IPvAnyAddress


class CreateModem(BaseModel):
    """
    Class represents fields for creating modem.
    """

    ip: IPvAnyAddress
    port: int = Field(lt=65536, gt=49152)
    bind_user_email: EmailStr
    username: str = Field(default=None)
    password: str = Field(default=None)


class ShowModem(BaseModel):
    """
    Class represents fields for displaying a modem.
    """

    id: int
    ip: IPvAnyAddress
    port: int
    hashed_value: str
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
    port: int = Field(lt=65536, gt=49152)
    username: str
    password: str
    rebooted: datetime | None


class ShowModemForUser(BaseModel):
    """
    Class represents modem info for displaying user info.
    """

    ip: IPvAnyAddress
    port: int
    rebooted: datetime | None
    created: datetime | None
