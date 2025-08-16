from datetime import datetime

from pydantic import BaseModel, Field


class CreateOTP(BaseModel):
    """Class represents fields for creating `OTP`."""

    user_id: int = Field(ge=1, description="User identifier who's bind to the OTP.")
    code: str = Field(max_length=64, description="Hashed value for randomly generated OTP.")
    expires_at: datetime = Field(description="Date and time when the OTP will be expired.")
