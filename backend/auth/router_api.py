import urllib.parse
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import timedelta
from secrets import compare_digest, token_urlsafe
from typing import Annotated, Any

import httpx
from auth.schemas import EnteredCheckOTP
from auth.utils import delete_cookie, set_cookie
from common.utils import get_base_url
from config import get_settings
from dependencies import DatabaseDependency, jwt_verification
from fastapi import (APIRouter, BackgroundTasks, Depends, Form, HTTPException,
                     Request, status)
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests
from google.oauth2 import id_token
from logs.logging_conf import get_endpoint_logger
from pydantic import EmailStr
from security import generate_hashed_otp, get_password_hash, verify_password
from sqlalchemy import delete, update
from users.crud import get_user_by_email
from users.models import User
from users.router_api import router
from users.utils import create_user_from_google
from validators import validate_email_format

from . import auth_bearer, crud, schemas, tasks
from .otp.models import OTP
from .otp.utils import send_otp_email_handler

settings = get_settings()
ENCODING = settings.default_encoding
templates = Jinja2Templates(directory="templates")
logger = get_endpoint_logger()
router = APIRouter()


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    description="Logging out from the system.",
    operation_id="logout",
    responses={
        200: {"description": "Successful"},
        401: {"description": "User not authorized"},
    },
)
async def logout(request: Request) -> JSONResponse:
    """
    Log out the user by clearing the authentication-related cookies
    (JWT and Google access token if available).

    The endpoint checks for the JWT token in the cookies. If the token is present,
    it will be deleted along with the Google access token (if set).
    The user will be logged out successfully, and they will be redirected to the login page.

    Returns:
        JSONResponse: A JSON response with a message indicating successful logout
        and a `redirect_url` to the login page.

    Raises:
        HTTPException: If no JWT token is found in the cookies
    """
    google_access_token = request.cookies.get(settings.cookies_google_access_token)
    jwt = request.cookies.get(settings.cookies_key_jwt)

    if jwt is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "You are not authorized.",
        )

    response = JSONResponse(
        {
            "message": "You are successfully logged out.",
            "redirect_url": str(request.url_for("login_page")),
        },
        status.HTTP_200_OK,
    )

    delete_cookie(response, settings.cookies_key_jwt)
    if google_access_token is not None:
        delete_cookie(response, settings.cookies_google_access_token)

    return response


@router.post(
    "/auth/revoke/google",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(jwt_verification)],
    response_class=JSONResponse,
    description="Revokes Google authentication and disconnects the user's Google account from the application.",
    operation_id="revoke-google-authentication",
    responses={
        200: {"description": "Successful"},
        401: {"description": "User not authorized via Google or token issuer is invalid"},
        400: {"description": "The token issuer is invalid."},
        412: {"description": "Token issuer is not Google"},
    },
)
async def revoke_google_auth(request: Request) -> JSONResponse:
    """
    Revokes Google authentication and disconnects the user's Google account from the application.

    The endpoint verifies the user's Google ID token, ensuring its validity, and revokes the
    Google access token by making a request to the Google OAuth 2.0 token revocation endpoint.
    It also deletes the relevant cookies storing these tokens.

    Args:
        request (Request): The HTTP request object, which contains cookies for the Google access
            token and ID token.

    Returns:
        JSONResponse: A JSON response confirming the successful revocation of Google authentication
        and deletion of cookies.

    Raises:
        HTTPException: If the Google tokens are missing, invalid, or issued by an unauthorized source.
    """
    google_access_token = request.cookies.get(settings.cookies_google_access_token)
    google_id_token = request.cookies.get(settings.cookies_key_jwt)

    if google_access_token is None and google_id_token is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "You are not authorized via Google.",
        )

    try:
        id_token_info: dict[str, Any] = id_token.verify_oauth2_token(
            google_id_token,
            requests.Request(),
            settings.google_client_id,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Token verification fails: {e}.") from e
    except GoogleAuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"The token issuer is invalid: {e}.") from e

    if id_token_info.get("iss", "") and id_token_info["iss"] != "https://accounts.google.com":
        raise HTTPException(status.HTTP_412_PRECONDITION_FAILED, "Token issuer is not Google.")

    async with httpx.AsyncClient() as client:
        google_response = await client.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": google_access_token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        google_response.raise_for_status()
        response = JSONResponse(
            {"message": "Your Google account has been successfully disconnected from the application."},
            status.HTTP_200_OK,
        )
        for key in (settings.cookies_key_jwt, settings.cookies_google_access_token):
            delete_cookie(response, key)

    return response


@router.get(
    "/auth/callback",
    name="google_login_callback",
    description="Handles the Google OAuth2 callback.",
    operation_id="handle-google-login",
    response_class=RedirectResponse,
    responses={
        "200": {"description": "Successful"},
        "400": {
            "description": "Authorization code or access token or ID token is missing",
        },
    },
)
async def google_login(request: Request, db: DatabaseDependency) -> RedirectResponse:
    """
    Handles the Google OAuth2 callback.

    The function is triggered after the user authorizes access via Google OAuth2.
    It exchanges the provided authorization code for an access token, retrieves user
    information from Google, and then either creates a new user in the database or
    confirms the user already exists.
    The user's ID token is set in a cookie for session persistence.

    Args:
        request (Request): The HTTP request, with the authorization code.
        db (DatabaseDependency): Database session used for user management and verification.

    Returns:
        RedirectResponse: Redirecting to the page which indicates successful login into the system.

    Raises:
        HTTPException: If the authorization code is missing,
            the access token retrieval fails or id token is missing.
    """
    code = request.query_params.get("code", "")
    if not code:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Missing code parameter.",
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": str(request.url_for("google_login_callback")),
            },
        )

        response.raise_for_status()
        token_data: dict[str, Any] = response.json()
        access_token: str = token_data.get("access_token", "")
        id_token: str = token_data.get("id_token", "")
        if not access_token:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "No access token received.",
            )

        if not id_token:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "No ID token received.",
            )

        user_info = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        user_email: str = user_info.json().get("email", "")
        if user_email:
            existing_user = get_user_by_email(db, user_email)
            if existing_user is None:
                create_user_from_google(user_email, db)

        response = RedirectResponse(str(request.url_for("index")))
        set_cookie(response, settings.cookies_key_jwt, id_token, max_age=token_data["expires_in"])
        set_cookie(response, settings.cookies_google_access_token, access_token, max_age=token_data["expires_in"])
        return response


@router.post(
    "/auth/login",
    response_class=JSONResponse,
    status_code=status.HTTP_200_OK,
    name="basic_login",
    description="Login in the system by getting access bearer token.",
    operation_id="basic-login",
    responses={
        400: {"description": "User no found or incorrect password or email"},
        200: {"description": "Successfully"},
    },
)
async def basic_login(
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=10, max_length=30)],
    db: DatabaseDependency,
    request: Request,
) -> JSONResponse:
    """
    Get JWT access token for provided user with `email` and `password`.

    Args:
        email (Annotated[EmailStr, Form): user email.
        password (Annotated[str, Form, optional): user password. Defaults to 10, max_length=30)].
        db (DatabaseDependency): database session.
        request(Request): HTTP request.

    Raises:
        HTTPException: the user with the given email does not exist.
        HTTPException: if entered email or password is incorrect.

    Returns:
        JSONResponse: response with the `redirect_url` content for using it
            for redirecting users to a page after successful authentication.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        logger.info(
            f"Email is invalid. Reason: {e}",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"email_invalid": str(e)}) from e

    user = db.query(User).filter(User.email == valid_email).first()
    if user is None:
        logger.info(
            f"User with the given email {valid_email} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, {"user_not_exists": "User with the given email does not exist."}
        )

    if not verify_password(password, str(user.hashed_password)):
        logger.info(
            "Incorrect email or password.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"incorrect_email_or_password": "Incorrect email or password."},
        )

    access_token_expires = timedelta(seconds=settings.access_token_expire_seconds)
    access_token: str = auth_bearer.create_access_token({"sub": user.email}, access_token_expires)
    response = JSONResponse({"redirect_url": str(request.url_for("index"))})
    set_cookie(response, settings.cookies_key_jwt, access_token, max_age=settings.access_token_expire_seconds)
    return response


@router.get(
    "/auth/login/google",
    name="login_google",
    response_class=RedirectResponse,
    description="Redirects the user to Google's OAuth2 authorization page.",
    operation_id="perform-google-auth",
)
async def perform_google_auth(request: Request) -> RedirectResponse:
    """
    Redirects the user to Google's OAuth2 authorization page.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        RedirectResponse: A redirect to Google's OAuth2 authorization URL.
    """
    google_auth_url = "https://accounts.google.com/o/oauth2/auth"
    query_params = {
        "client_id": settings.google_client_id,
        "redirect_uri": str(request.url_for("google_login_callback")),
        "state": token_urlsafe(),
        "access_type": "offline",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/userinfo.email",
        "include_granted_scopes": "true",
    }
    google_auth_url = f"{google_auth_url}?{urllib.parse.urlencode(query_params)}"
    return RedirectResponse(url=google_auth_url)


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
        JSONResponse: response with the message with info about verification
            registered email.
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

    token = token_urlsafe(32)[: settings.unique_user_token_length]
    crud.register_regular_user(db, body, token)

    await send_otp_email_handler(bg_tasks, request, token, db)
    return JSONResponse(
        {"message": "Check your email for verifying your account."},
        status.HTTP_200_OK,
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
    and sends to them an email message with the link for confirm password reset.

    Args:
        request (Request): HTTP request.
        body (schemas.ResetPassword): request body with email field.
        bg_tasks (BackgroundTasks): background task implemented by FastAPI.
        db (DatabaseDependency): database session.

    Raises:
        HTTPException: If user does not exist by the entered email.

    Returns:
        JSONResponse: response with message, which will be displayed to a client.
    """
    db_user = db.query(User).filter(User.email == body.email).first()
    if db_user is None:
        logger.info(f"User with the given email {body.email} does not exist.")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email does not exist.")

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
    "/auth/send_verification_email/",
    name="send_verification_email",
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    operation_id="send-email-otp",
    description="Send an email message with OTP to a user email for verification the user's email after registration.",
    responses={200: {"description": "Successful"}},
)
async def send_otp_email(
    request: Request,
    body: schemas.RecheckOTPOnDemand,
    db: DatabaseDependency,
    bg_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Sends OTP to a user using FastAPI background tasks implementation.

    Args:
        request (Request): HTTP request.
        body (schemas.VerificationEmailUserData): Pydantic model with the user data for sending verification email.
        db (DatabaseDependency): database dependency injection.
        bg_tasks (BackgroundTasks): FastAPI background task implementation.

    Returns:
        JSONResponse: JSON response with the status of sending an email.
    """
    await send_otp_email_handler(bg_tasks, request, body.token, db, body.uid)
    return JSONResponse("Email has been sent successfully.", status.HTTP_200_OK)


@router.post(
    "/auth/compare_codes/",
    name="compare_codes",
    response_class=JSONResponse,
    status_code=status.HTTP_200_OK,
    description="Compare OTP received from a client with OTP saved in database.",
    operation_id="compare-codes-for-verify-email",
    responses={
        200: {"description": "Successful"},
        400: {"description": "Code is incorrect or expired"},
    },
)
async def compare_codes(request: Request, body: EnteredCheckOTP, db: DatabaseDependency) -> JSONResponse:
    """
    Compare OTP received from a client with OTP saved in database
    in order to verify user's email.

    If provided by user OTP will turn to be the same as OTP from the DB,
    then the user's `is_verified` field will be set as True.

    Args:
        body (EnteredCheckOTP): HTTP Request body:
            - entered OTP from a client,
            - user ID in urlsafe_base64 format,
            - user token.
        db (DatabaseDependency): database session.
        request (Request): HTTP request.

    Returns:
        JSONResponse: HTTP response with status about correctness of the provided code by a client.
    """

    def delete_otp(pk: int) -> None:
        """
        Delete OTP, related to user, from the DB if it was expired or successfully
        compared with the OTP provided by the user.

        Args:
            pk (int): OTP primary key.
        """
        stmt = delete(OTP.__table__).where(OTP.id == pk)
        db.execute(stmt)
        db.commit()

    entered_otp_plain = body.entered_otp
    entered_otp_hashed = generate_hashed_otp(entered_otp_plain)

    db_otp_hashed = (
        db.query(OTP)
        .join(User)
        .filter(
            User.id == urlsafe_b64decode(body.uid).decode(ENCODING),
            OTP.code == entered_otp_hashed,
        )
    ).first()

    if db_otp_hashed is None:
        logger.info(
            "Provided OTP does not exist in the database.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        return JSONResponse(
            {"error": "The code you entered is incorrect."},
            status.HTTP_400_BAD_REQUEST,
        )

    if db_otp_hashed.is_expired:
        delete_otp(db_otp_hashed.id)  # type: ignore
        return JSONResponse(
            {"error": "Code is expired."},
            status.HTTP_400_BAD_REQUEST,
        )

    # mark the user as verified their email
    setattr(db_otp_hashed.user, "is_verified", True)
    db.commit()
    delete_otp(db_otp_hashed.id)  # type: ignore

    base_url = get_base_url(request)
    index_page_path = request.url_for("index").components.path
    index_page_url = f"{base_url}{index_page_path}"

    return JSONResponse(
        {
            "success": "The code you entered is correct. Email has been verified.",
            "index_page_url": index_page_url,
        },
        status.HTTP_200_OK,
    )
