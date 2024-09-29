from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """
    Class represents fields for JWT response.
    """

    access_token: str
    token_type: str = Field(default="bearer")


class TokenData(BaseModel):
    """
    Class represents data which contains JWT.
    """

    email: str | None = None


class RegisterUser(BaseModel):
    """
    Class represents fields for user registration.
    """

    email: EmailStr
    password: str = Field(min_length=10, max_length=30)


class ResetPassword(BaseModel):
    """
    Class represents fields for requesting password reset.
    """

    email: EmailStr = Field(
        description="User email, which the user used while registration.",
        examples=["example@gmail.com"],
    )


class ResetPasswordConfirm(BaseModel):
    """
    Class represents fields for confirm password reset.
    """

    new_password: str = Field(max_length=30, min_length=10)
    confirm_password: str = Field(max_length=30, min_length=10)
    uid: str = Field(description="User ID encoded in 'base64-urlsafe' format.")
    token: str = Field(
        max_length=32,
        min_length=32,
        description="Unique user token which generates automatically during user registration.",
    )


class EnteredCheckOTP(BaseModel):
    """
    Class represents fields for verifying entered OTP
    along with identifying a user by the given uid and token from URL.
    """

    entered_otp: str = Field(
        description=(
            "OTP which user entered in the browser after "
            "following by the link in the user's email after registration."
        )
    )
    uid: str
    token: str = Field(max_length=32, min_length=32)


class RecheckOTPOnDemand(BaseModel):
    """
    Class represents fields for re-checking entered OTP,
    if a user requested another one OTP when the OTP was
    expired or not correct.
    """

    uid: str
    token: str = Field(max_length=32, min_length=32)
