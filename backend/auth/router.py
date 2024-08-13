from datetime import timedelta
from typing import Annotated

from config import get_settings
from dependencies import DatabaseDependency
from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from security import verify_password
from users.models import User
from users.schemas import UserRole

from .auth_bearer import create_access_token
from .schemas import Token

settings = get_settings()

router = APIRouter()


@router.post(
    "/token/",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    description="Get access bearer token.",
    operation_id="get-access-token",
    responses={
        400: {"description": "User no found or incorrect password or email"},
        200: {"description": "Successfully"},
    },
)
async def get_access_token(
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=10, max_length=30)],
    db: DatabaseDependency,
) -> JSONResponse:
    """
    Get JWT access token for provided user with `email` and `password`.
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email does not exist.")

    if user.role.name != UserRole.ADMIN.name:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access token available only for admin users.")

    if not verify_password(password, str(user.hashed_password)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect email or password.")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token: str = create_access_token({"sub": user.email}, access_token_expires)

    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
        },
        status.HTTP_200_OK,
    )
