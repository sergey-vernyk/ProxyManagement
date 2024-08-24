from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from ipaddress import IPv4Address

from pydantic import BaseModel, EmailStr, Field, HttpUrl, IPvAnyAddress


class ModemAction(str, Enum):
    """
    Actions for interaction with a modem.
    """

    REBOOT = "reboot"
    GET_IP = "get_ip"


@dataclass(kw_only=True)
class ModemActionsData:
    """
    Class holds data which used for interaction with a modem.
    """

    ip: IPv4Address
    port: int
    internal_server_ip: IPv4Address
    proxy_login: str
    proxy_password_plain: str
    action: ModemAction
    username: str | None = None
    password: str | None = None

    def __post_init__(self) -> None:
        if not 49152 < self.port < 65536:
            raise ValueError(f"Port value must be within 49152 and 65536. {self.port} was provided.")

    def convert_to_string_to_send(self) -> str:
        """
        Method converts data in the class to string,
        in which values are separated by commas.
        """
        data = [
            str(self.ip),
            str(self.port),
            str(self.internal_server_ip),
            self.proxy_login,
            self.proxy_password_plain,
            self.action,
        ]
        if self.username is not None and self.password is not None:
            data.extend([self.username, self.password])

        return ",".join(data)


class CreateModem(BaseModel):
    """
    Class represents fields for creating modem.
    """

    ip: IPvAnyAddress
    port: int = Field(lt=65536, gt=49152)
    external_server_ip: IPvAnyAddress | None = None
    internal_server_ip: IPvAnyAddress | None = None
    bind_user_email: EmailStr | None = None
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)


class ShowModem(BaseModel):
    """
    Class represents fields for displaying a modem.
    """

    id: int
    ip: IPvAnyAddress
    external_server_ip: IPvAnyAddress | None
    internal_server_ip: IPvAnyAddress | None
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
    external_server_ip: IPvAnyAddress | None = None
    internal_server_ip: IPvAnyAddress | None = None
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
    external_server_ip: IPvAnyAddress | None
    internal_server_ip: IPvAnyAddress | None
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
    external_server_ip: IPv4Address | None = None
    internal_server_ip: IPv4Address | None = None
    url: HttpUrl
