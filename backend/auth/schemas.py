from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """
    Define data types for token.
    """

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Data for get email from the given token.
    """

    email: str | None = None


class RegisterUser(BaseModel):
    """
    Class represents fields for user registration.
    """

    email: EmailStr
    password: str = Field(min_length=10, max_length=30)
