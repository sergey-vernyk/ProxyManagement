from datetime import timedelta
from typing import Annotated

from config import get_settings
from dependencies import DatabaseDependency
from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from security import verify_password
from users.crud import get_user_by_email

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
    db_user = get_user_by_email(db, email)
    if db_user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email does not exist.")

    if not verify_password(password, str(db_user.hashed_password)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect email or password.")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token: str = create_access_token({"sub": db_user.email}, access_token_expires)

    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
        },
        status.HTTP_200_OK,
    )
