from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import timedelta
from secrets import compare_digest, token_urlsafe
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
from security import get_password_hash, verify_password
from sqlalchemy import update
from starlette.templating import _TemplateResponse
from users.crud import get_user_by_email
from users.models import User
from users.schemas import UserRole
from validators import validate_email_format

from . import auth_bearer, crud, schemas, tasks
from .otp.utils import send_otp_email_handler

settings = get_settings()
ENCODING = settings.default_encoding
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
    body: schemas.RegisterUser,
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
    crud.register_regular_user(db, body, token)

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
    operation_id="user-registration-page",
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
    operation_id="user-registration-success-page",
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


@router.get(
    "/users/reset_password/",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    name="reset_password_page",
    operation_id="reset-password-page",
    description="Reset user password.",
    responses={200: {"description": "Successful"}},
)
async def reset_password_page(request: Request) -> _TemplateResponse:
    """
    Page which will be displayed form for enter user email for reset password.

    Args:
        request (Request): HTTP request

    Returns:
        _TemplateResponse: template `reset_password.html` with the reset password url link.
    """
    base_url = get_base_url(request)
    reset_password_path = request.url_for("reset_password").components.path
    reset_password_url = f"{base_url}{reset_password_path}"
    return templates.TemplateResponse(
        request,
        name="reset_password.html",
        context={"reset_password_url": reset_password_url},
    )


@router.get(
    "/users/reset_password_confirm/{uid}/{token}",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    name="reset_password_confirm_page",
    operation_id="reset-password-confirm-page",
    description="Confirm resetting user password after following the link in user email box.",
    responses={200: {"description": "Successful"}},
)
async def reset_password_confirm_page(request: Request, uid: str, token: str) -> _TemplateResponse:
    """
    A page that will display a form for entering passwords that will be compared.
    And if the passwords are the same, then this new password will be set for the user.

    Args:
        request (Request): HTTP request.
        uid (str): user ID encoded in base64_urlsafe format.
        token (str): user token.

    Returns:
        _TemplateResponse: template `reset_password_confirm.html`
            with the confirm reset password url link uid and token.
    """
    base_url = get_base_url(request)
    reset_password_confirm_path = request.url_for("reset_password_confirm").components.path
    reset_password_confirm_url = f"{base_url}{reset_password_confirm_path}"
    return templates.TemplateResponse(
        request,
        name="reset_password_confirm.html",
        context={
            "reset_password_confirm_url": reset_password_confirm_url,
            "uid": uid,
            "token": token,
        },
    )


@router.post(
    "/auth/reset_password",
    status_code=status.HTTP_200_OK,
    name="reset_password",
    response_class=JSONResponse,
    operation_id="reset-password",
    description=(
        "Reset user password. User enter their password and if the password is correct, "
        "the user will get an email message with reset password link."
    ),
    responses={
        200: {"description": "Successful"},
        400: {"description": "User does not exist."},
    },
)
async def reset_password(
    request: Request, body: schemas.ResetPassword, bg_tasks: BackgroundTasks, db: DatabaseDependency
) -> JSONResponse:
    """
    Attempts to find in database a user to the entered email
    and sends to they an email message with the link for confirm password reset.

    Args:
        request (Request): HTTP request.
        body (schemas.ResetPassword): request body with email field.
        bg_tasks (BackgroundTasks): background task implemented by FastAPI.
        db (DatabaseDependency): database session.

    Raises:
        HTTPException: If user does not exists by the entered email.

    Returns:
        JSONResponse: response with message, which will be displayed to a client.
    """
    db_user = db.query(User).filter(User.email == body.email).first()
    if db_user is None:
        logger.info(f"User with the given email {body.email} does not exist.")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email doe not exist.")

    base_url = get_base_url(request)
    uid = urlsafe_b64encode(str(db_user.id).encode(ENCODING)).decode(ENCODING)
    reset_link_path = request.url_for("reset_password_confirm_page", uid=uid, token=db_user.token).components.path
    reset_link_url = f"{base_url}{reset_link_path}"

    bg_tasks.add_task(
        tasks.send_reset_password_email,
        user_email=body.email,
        context={
            "email": body.email,
            "reset_link": reset_link_url,
        },
    )

    return JSONResponse(
        "Email message with the link for password reset has been sent to your email.",
        status.HTTP_200_OK,
    )


@router.post(
    "/auth/reset_password_confirm",
    status_code=status.HTTP_200_OK,
    name="reset_password_confirm",
    response_class=JSONResponse,
    operation_id="reset-password-confirm",
    description=(
        "Reset user password confirmation. "
        "User should enter new password and confirm the new password by enter the same password as before."
    ),
    responses={
        200: {"description": "Successful"},
        400: {"description": "Passwords are mismatch or reset link is invalid"},
    },
)
async def reset_password_confirm(body: schemas.ResetPasswordConfirm, db: DatabaseDependency) -> JSONResponse:
    """
    Compares passwords, entered by the client.
    If the passwords will turn to be the same, then decodes UID,
    get a user from database by their ID and set they the new password (hashed it before).

    Args:
        body (schemas.ResetPasswordConfirm): request body with:
            - new password,
            - confirmed new password,
            - uid,
            - token.
        db (DatabaseDependency): database session.

    Raises:
        HTTPException: If the given password are mismatch.
        HTTPException: If the the URL link in user's email is invalid.

    Returns:
        JSONResponse: response with the message that the password has been reset.
    """
    new_password = body.new_password
    password_confirm = body.confirm_password

    if not compare_digest(new_password, password_confirm):
        logger.info("Entered passwords are mismatch.")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Entered passwords are mismatch.")

    user_id = int(urlsafe_b64decode(body.uid).decode(ENCODING))
    db_user = db.query(User).filter(User.id == user_id, User.token == body.token).first()
    if db_user is None:
        logger.info("Password reset link is invalid.")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password reset link is invalid.")

    stmt = update(User.__table__).where(User.id == user_id).values(hashed_password=get_password_hash(new_password))
    db.execute(stmt)
    db.commit()

    return JSONResponse("Password has been reset successfully.", status.HTTP_200_OK)


@router.post(
    "/auth/token",
    response_model=schemas.Token,
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
    access_token: str = auth_bearer.create_access_token({"sub": user.email}, access_token_expires)

    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
        },
        status.HTTP_200_OK,
    )
