from modems.schemas import ShowModemForUser
from pydantic import BaseModel, EmailStr, Field


class CreateUser(BaseModel):
    """
    Class represents fields for creating  a user.
    """

    email: EmailStr
    login: str


class ShowUser(BaseModel):
    """
    Class represents fields for displaying user.
    """

    id: int
    email: EmailStr
    token: str = Field(max_length=32)
    login: str
    password: str
    user_modems: list[ShowModemForUser]


class UpdateUserCredentials(BaseModel):
    """
    Class for defining proxy credentials fields for updating.
    """

    login: str
    password: str
