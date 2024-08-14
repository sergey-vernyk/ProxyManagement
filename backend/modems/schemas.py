from datetime import datetime
from ipaddress import IPv4Address

from pydantic import BaseModel, EmailStr, Field, HttpUrl, IPvAnyAddress


class CreateModem(BaseModel):
    """
    Class represents fields for creating modem.
    """

    ip: IPvAnyAddress
    port: int = Field(lt=65536, gt=49152)
    public_server_ip: IPvAnyAddress | None = None
    bind_user_email: EmailStr | None = None
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)


class ShowModem(BaseModel):
    """
    Class represents fields for displaying a modem.
    """

    id: int
    ip: IPvAnyAddress
    public_server_ip: IPvAnyAddress | None
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
    public_server_ip: IPvAnyAddress | None = None
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
    public_server_ip: IPvAnyAddress | None
    port: int
    hashed_value: str | None
    rebooted: datetime | None
    created: datetime | None


class ChangeIPUrl(BaseModel):
    """
    Class represents fields for changing ip of a modem (via rebooting it).
    """

    ip: IPv4Address
    port: int
    public_server_ip: IPv4Address | None = None
    url: HttpUrl
