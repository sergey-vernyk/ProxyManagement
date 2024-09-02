from datetime import timedelta
from secrets import token_urlsafe
from typing import Annotated

from common.utils import get_base_url
from config import get_settings
from dependencies import DatabaseDependency
from fastapi import (APIRouter, BackgroundTasks, Form, HTTPException, Request,
                     status)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from logs.logging_conf import get_endpoint_logger
from pydantic import EmailStr
from security import verify_password
from starlette.templating import _TemplateResponse
from users.crud import get_user_by_email
from users.models import User
from users.schemas import UserRole
from validators import validate_email_format

from .auth_bearer import create_access_token
from .crud import register_regular_user
from .otp.utils import send_otp_email_handler
from .schemas import RegisterUser, Token

settings = get_settings()
templates = Jinja2Templates(directory="templates")
logger = get_endpoint_logger()
router = APIRouter()


@router.post(
    "/auth/registration",
    response_class=JSONResponse,
    name="registration",
    status_code=status.HTTP_201_CREATED,
    description="Register a user for a modem.",
    operation_id="register-regular-user",
    responses={
        201: {"description": "User registered"},
        400: {"description": "User already registered or invalid email format"},
    },
)
async def register_user(
    request: Request,
    body: RegisterUser,
    db: DatabaseDependency,
    bg_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Register regular user for a modem.

    Args:
        request (Request): HTTP request.
        body (RegisterUser): HTTP request body with email and password.
        db (DatabaseDependency): database session.
        bg_tasks (BackgroundTasks): Background tasks implemented by FastAPI.

    Raises:
        HTTPException: If the user with the provided email is already registered.
            If the given email is invalid.

    Returns:
        JSONResponse: response with the `redirect_url` content for using it
            for redirecting users to a page after successful registration.
    """
    try:
        valid_email = validate_email_format(body.email)
    except ValueError as e:
        logger.info(
            f"Email is invalid. Reason: {e}",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"email_invalid": str(e)}) from e

    db_user = get_user_by_email(db, valid_email)
    if db_user is not None:
        logger.info(
            f"User with the given email {body.email} is already registered.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"user_exists": "User with the given email is already registered."},
        )

    token = token_urlsafe(32)[:32]
    register_regular_user(db, body, token)

    await send_otp_email_handler(bg_tasks, request, token, db)
    return JSONResponse(
        {"redirect_url": f"{request.url_for('success_registration')}"},
        status.HTTP_201_CREATED,
    )


@router.get(
    "/users/signup/",
    status_code=status.HTTP_200_OK,
    response_class=HTMLResponse,
    include_in_schema=False,
    operation_id="user-registration",
    description="Provides user registration with email and password.",
    responses={200: {"description": "Successful"}},
)
async def registration_page(request: Request) -> _TemplateResponse:
    """
    Page for registration.

    Args:
        request (Request): HTTP request.

    Returns:
        _TemplateResponse: template `registration.htm` with the server registration URL.
    """
    base_url = get_base_url(request)
    reg_path = request.url_for("registration").components.path
    reg_url = f"{base_url}{reg_path}"

    return templates.TemplateResponse(request, name="registration.html", context={"reg_url": reg_url})


@router.get(
    "/users/success_signup/",
    status_code=status.HTTP_200_OK,
    response_class=HTMLResponse,
    name="success_registration",
    include_in_schema=False,
    operation_id="user-registration-success",
    description="Redirect to this page after successful registration.",
    responses={200: {"description": "Successful"}},
)
async def success_registration_page(request: Request) -> _TemplateResponse:
    """
    Page which will be displayed after successful registration.

    Args:
        request (Request): HTTP request.

    Returns:
        _TemplateResponse: template `registration_success.html` with the message.
    """
    return templates.TemplateResponse(
        request,
        name="registration_success.html",
        context={"message": "Check your email for verifying your account."},
    )


@router.post(
    "/auth/token",
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

    Args:
        email (Annotated[EmailStr, Form): user email.
        db (DatabaseDependency): database session.
        password (Annotated[str, Form, optional): user password. Defaults to 10, max_length=30)].

    Raises:
        HTTPException: the user with the given email does not exist.
        HTTPException: if regular user tries to get access token, which available only for admin users.
        HTTPException: if entered email or password is incorrect.

    Returns:
        JSONResponse: response with keys `access_token` and `token_type`.
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
