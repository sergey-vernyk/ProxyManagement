from pydantic import BaseModel, EmailStr, Field, IPvAnyAddress


class CreateModem(BaseModel):
    """
    Class represents fields for creating modem.
    """

    modem_ip: IPvAnyAddress
    token: str
    bind_user_id: int
    modem_username: str = Field(default=None)
    modem_password: str = Field(default=None)


class CreateUser(BaseModel):
    """
    Class represents fields for creating a user.
    """

    email: EmailStr
    login: str
    password: str


class UserShow(BaseModel):
    """
    Class represents fields for displaying user
    """

    id: int
    email: EmailStr
