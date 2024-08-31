from datetime import datetime

from pydantic import BaseModel, Field


class CreateOTP(BaseModel):
    """
    Class represents fields for creating OTP.
    """

    user_id: int = Field(gt=1)
    code: str = Field(max_length=64)
    expires_at: datetime
