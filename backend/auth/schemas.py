from pydantic import BaseModel


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
