from datetime import datetime

from pydantic import BaseModel, Field, IPvAnyAddress


class CreateModem(BaseModel):
    """
    Class represents fields for creating modem.
    """

    modem_ip: IPvAnyAddress
    modem_port: int = Field(lt=65536, gt=49152)
    bind_user_id: int
    modem_username: str = Field(default=None)
    modem_password: str = Field(default=None)


class ShowModem(BaseModel):
    """
    Class represents fields for displaying a modem.
    """

    id: int
    modem_ip: IPvAnyAddress
    modem_username: str
    modem_password: str
    rebooted: datetime
    created: datetime
    updated: datetime


class UpdateModem(BaseModel):
    """
    Class represents fields for updating a modem.
    """

    modem_ip: IPvAnyAddress
    modem_username: str
    modem_password: str
    rebooted: datetime


class ShowModemForUser(BaseModel):
    """
    Class represents modem info for displaying user info.
    """

    modem_ip: IPvAnyAddress
    rebooted: datetime
    created: datetime
