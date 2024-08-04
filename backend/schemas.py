from pydantic import BaseModel, EmailStr, Field, IPvAnyAddress


class CreateModem(BaseModel):
    """
    Class represents fields for creating modem.
    """

    modem_ip: IPvAnyAddress
    token: str
    bind_user: EmailStr
    modem_username: str = Field(default=None)
    modem_password: str = Field(default=None)
