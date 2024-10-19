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
        if not 49152 <= self.port <= 65000:
            raise ValueError(f"Port value must be within 49152 and 65000 inclusive. {self.port} was provided.")

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
    Class represents fields for creating a modem.
    """

    ip: IPvAnyAddress = Field(
        description="Modem IP address in the server network.",
        examples=["192.168.9.1"],
    )
    port: int = Field(le=65000, ge=49152, description="Server port assigned to a modem.")
    external_server_ip: IPvAnyAddress | None = Field(
        default=None,
        description="Server external IP, where a modem is connected.",
        examples=["45.196.29.178"],
    )
    external_server_port: int = Field(
        description=(
            "Server port, where a proxy is located and "
            "the socket client can connect via this port to the socket server."
        ),
        le=65535,
        ge=65000,
    )
    external_server_host: HttpUrl = Field(
        description="Public host of the server where a proxy is located.",
        examples=["https://example.com"],
    )
    internal_server_ip: IPvAnyAddress | None = Field(
        default=None,
        description=(
            "Server internal IP, where a modem is connected (internal address in the LAN). Used for getting modem IP."
        ),
        examples=["192.168.1.105"],
    )
    bind_user_email: EmailStr | None = Field(
        default=None,
        description="User email, who bind to a modem.",
        examples=["ananymous@gmail.com"],
    )
    username: str | None = Field(
        default=None,
        description="Modem username for accessing to its API or WebUI.",
        examples=["admin"],
    )
    password: str | None = Field(
        default=None,
        description="Modem password for accessing to its API or WebUI.",
        examples=["password"],
    )


class ShowModem(BaseModel):
    """
    Class represents fields for displaying a modem.
    """

    id: int
    ip: IPvAnyAddress
    external_server_ip: IPvAnyAddress | None
    internal_server_ip: IPvAnyAddress | None
    external_server_port: int
    external_server_host: HttpUrl
    port: int
    hashed_value: str | None
    bind_user_email: str | None
    username: str | None
    password: str | None
    rebooted: datetime | None = Field(description="Time when a modem was rebooted for the last time.")
    created: datetime
    updated: datetime | None


class UpdateModem(BaseModel):
    """
    Class represents fields for updating a modem.
    """

    ip: IPvAnyAddress
    external_server_ip: IPvAnyAddress | None = None
    internal_server_ip: IPvAnyAddress | None = None
    external_server_port: int = Field(le=65535, ge=65000, default=None)
    external_server_host: HttpUrl
    update_hashed_value: bool = Field(
        description="Flag for indicating a user intention to update modem 'hashed_value' field.",
        default=False,
    )
    bind_user_email: EmailStr | None = None
    port: int | None = Field(le=65000, ge=49152, default=None)
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
    external_server_host: HttpUrl
    port: int
    hashed_value: str | None = Field(description="Unique value for each modem.")
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
    external_server_host: HttpUrl
    last_change_ip: str
    url: HttpUrl = Field(
        description="Url for rebooting a modem (change its IP).",
        examples=[
            "http://127.0.0.1:8000/modems/u-oyq9j3aihaqLPlduOT46y-_CfWQUI8/a9b38e70d9500981251034cd2107a37c",
            "http://example.com/modems/u-oyq9j3aihaqLPlduOT46y-_CfWQUI8/a9b38e70d950051034cd2107a37c",
        ],
    )
