"""
Module contains endpoints for users:
- create_user
- get_user
- get_users
- update_user_proxy_credentials
- update_user
- delete_user
"""

import random
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Annotated, Any

from auth.auth_bearer import JWTBearer
from auth.otp import crud as otp_crud
from auth.otp import schemas as otp_schemas
from auth.otp.models import OTP
from common.utils import get_base_url
from config import get_settings
from dependencies import DatabaseDependency
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException, Query,
                     status)
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from logs.logging_conf import get_endpoint_logger
from modems.crud import get_modem_by_ip
from pydantic import EmailStr, IPvAnyAddress
from security import (encrypt_modem_password, generate_hashed_otp,
                      generate_md5_crypt_hash_password, generate_random_otp,
                      get_password_hash, verify_password)
from sqlalchemy import delete
from starlette.templating import _TemplateResponse
from validators import validate_email_format

from . import crud, models, schemas, tasks

settings = get_settings()
ENCODING = settings.default_encoding
templates = Jinja2Templates(directory="templates")

logger = get_endpoint_logger()
router = APIRouter()


@router.post(
    "/users/",
    response_model=schemas.ShowUser,
    status_code=status.HTTP_201_CREATED,
    description="Create a user for a modem.",
    operation_id="create-user",
    responses={
        201: {"description": "User created"},
        400: {"description": "User already registered or invalid email format"},
    },
)
async def create_user(
    request: Request,
    body: schemas.CreateRegularUser | schemas.CreateAdminUser,
    db: DatabaseDependency,
    bg_tasks: BackgroundTasks,
) -> models.User:
    """
    Create a user or raise an exception if user with provided email is already exists.
    """

    def create_otp() -> str:
        """
        Create OTP, create OPT object with the created OTP plain string.

        Returns:
            str: random plain OTP.
        """
        otp_code = generate_random_otp()
        otp_expires = datetime.now() + timedelta(minutes=settings.otp_expire_time)
        otp_data = otp_schemas.CreateOTP(user_id=int(user.id), code=generate_hashed_otp(otp_code), expires_at=otp_expires)  # type: ignore
        otp_crud.create_otp(db, otp_data)
        return otp_code

    try:
        valid_email = validate_email_format(body.email)
    except ValueError as e:
        logger.info(
            f"Email is invalid. Reason: {e}",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is not None:
        logger.info(
            f"User with the given email {body.email} is already registered.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email is already registered.")

    token: str | None = None
    proxy_login: str | None = None
    proxy_password_hashed: str | None = None

    if isinstance(body, schemas.CreateRegularUser):
        token = token_urlsafe(32)[:32]
        proxy_login = token_urlsafe(32)[: random.randint(10, 20)]

        if body.proxy_password_hash_type is not None:
            if body.proxy_password_hash_type == schemas.HashType.MD5:
                proxy_password_hashed = generate_md5_crypt_hash_password(body.proxy_password_plain)
            else:
                proxy_password_hashed = encrypt_modem_password(body.proxy_password_hash_type, body.proxy_password_plain)

    user = crud.create_user(
        db,
        body,
        token,
        proxy_login,
        proxy_password_hashed,
    )

    base_url = get_base_url(request)
    uid = urlsafe_b64encode(str(user.id).encode(ENCODING)).decode(ENCODING)
    path = f"users/verify_email/{uid}/{user.token}"
    verification_url = f"{base_url}{path}"

    bg_tasks.add_task(
        tasks.send_verification_email,
        str(user.email),
        context={
            "email": user.email,
            "otp_code": create_otp(),
            "verification_url": verification_url,
            "otp_expire_time": settings.otp_expire_time,
        },
    )
    return user


@router.get(
    "/users/",
    response_model=list[schemas.ShowUser],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Get all users within `skip` and `limit` params.",
    operation_id="get-users",
    responses={200: {"description": "Successfully"}},
)
async def get_users(
    db: DatabaseDependency,
    user_type: Annotated[str, Query(description="Type of user: admin or regular.", default="regular")] | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[models.User]:
    """
    Returns all users between `skip` and `limit` that are `admin`, `regular`, or any of them.
    """
    return crud.get_users(db, user_type, offset=skip, limit=limit)


@router.get(
    "/users/{email}",
    response_model=schemas.ShowUser,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Get a user by the given email.",
    operation_id="get-user-by-email",
    responses={
        404: {"description": "User not found"},
        400: {"description": "Invalid email format"},
        200: {"description": "Successfully"},
    },
)
async def get_user(request: Request, email: EmailStr, db: DatabaseDependency) -> models.User:
    """
    Returns a user by its `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        logger.info(
            f"Email is invalid. Reason: {e}",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
        logger.info(
            f"User with the given email {email} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exist.")

    return db_user


@router.patch(
    "/users/proxy/{ip}",
    response_model=schemas.ShowUser,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Update a proxy credentials for a modem with IP bind to user.",
    operation_id="update-user-proxy-credentials",
    responses={
        400: {"description": "Invalid email format"},
        404: {"description": "User not found"},
        200: {"description": "Successfully"},
    },
)
async def update_user_proxy_credentials(
    request: Request, ip: IPvAnyAddress, body: schemas.UpdateUserProxyCredentials, db: DatabaseDependency
) -> models.User:
    """
    Update user credentials for proxy.
    """
    db_modem = get_modem_by_ip(db, str(ip))
    if db_modem is None:
        logger.info(
            f"Modem with the given IP {ip} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exists.")

    proxy_password: str | None = None

    if body.proxy_password_plain is not None and body.proxy_password_hash_type is not None:
        if body.proxy_password_hash_type == schemas.HashType.MD5:
            proxy_password = generate_md5_crypt_hash_password(body.proxy_password_plain)
        else:
            proxy_password = encrypt_modem_password(body.proxy_password_hash_type, body.proxy_password_plain)
    else:
        proxy_password = body.proxy_password_plain

    data_to_update = body.model_dump(exclude_unset=True, exclude={"password_hash_type", "update_login"})

    if "proxy_password" in data_to_update:
        data_to_update["proxy_password"] = proxy_password
    if body.update_login:
        data_to_update["proxy_login"] = token_urlsafe(32)[: random.randint(10, 20)]

    return crud.update_user_proxy_credentials(db, db_modem.bind_user, data_to_update)


@router.put(
    "/users/{email}",
    response_model=schemas.ShowUser,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Update a user by the given email.",
    operation_id="update-user",
    responses={
        404: {"description": "User not found"},
        400: {"description": "Invalid email format"},
        200: {"description": "Successfully"},
    },
)
async def update_user(
    request: Request, email: EmailStr, body: schemas.UpdateUser, db: DatabaseDependency
) -> models.User:
    """
    Update user info with `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        logger.info(
            f"Email is invalid. Reason: {e}",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
        logger.info(
            f"User with the given email {email} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exists.")

    data_to_update: dict[str, Any] = {}

    if body.update_password and body.old_password is not None and body.new_password is not None:
        if not verify_password(body.old_password, str(db_user.hashed_password)):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Entered old password not matches with the existing user password."
            )
        data_to_update["hashed_password"] = get_password_hash(body.new_password)

    if body.update_token:
        token = token_urlsafe(32)[:32]
        data_to_update["token"] = token

    data_to_update["email"] = body.email

    return crud.update_user_info(db, db_user, data_to_update)


@router.delete(
    "/users/{email}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete a user by the given email.",
    dependencies=[Depends(JWTBearer())],
    operation_id="delete-user-by-email",
    responses={
        400: {"description": "Invalid email format"},
        404: {"description": "User not found"},
        200: {"description": "Successfully"},
    },
)
async def delete_user(request: Request, email: EmailStr, db: DatabaseDependency) -> None:
    """
    Delete user with the given `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        logger.info(
            f"Email is invalid. Reason: {e}",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
        logger.info(
            f"User with the given email {email} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email is not exists.")

    crud.delete_user(db, valid_email)


@router.get(
    "/users/verify_email/{uid}/{token}",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    operation_id="verify-user-email",
    include_in_schema=False,
)
async def verify_email_page(request: Request, uid: str, token: str) -> _TemplateResponse:
    """
    HTTP GET endpoint to serve user's email verification page.
    User will be on the page, after following by URL in their email after registration.

    Args:
        request (Request): HTTP request.
        uid (str): user ID, encoded in base64_urlsafe format.
        token (str): user token which generates after user registration.

    Returns:
        _TemplateResponse: Renders the "verify_email.html" template.
    """
    base_url = get_base_url(request)
    path = "users/compare_codes/"
    compare_codes_url = f"{base_url}{path}"

    return templates.TemplateResponse(
        request,
        name="verify_otp.html",
        context={
            "compare_codes_url": compare_codes_url,
            "uid": uid,
            "token": token,
        },
    )


@router.post(
    "/users/compare_codes/",
    response_class=JSONResponse,
    status_code=status.HTTP_200_OK,
    operation_id="compare-codes-for-verify-email",
    responses={
        200: {"description": "Successful"},
        400: {"description": "Code is incorrect or expired"},
    },
)
async def compare_codes(body: schemas.CheckOTP, db: DatabaseDependency) -> JSONResponse:
    """
    Compare OTP received from a client with OTP saved in database
    in order to verify user's email.

    If provided by user OTP will turn to be the same as OTP from the DB,
    then the user's `is_verified` field will be set as True.

    Args:
        body (schemas.CheckOTP): HTTP Request body:
            - entered OTP from a client,
            - user ID in urlsafe_base64 format,
            - user token.
        db (DatabaseDependency): database session.

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

    code_incorrect_response = JSONResponse(
        {"error": "The code you entered is incorrect. Please, try again."},
        status.HTTP_400_BAD_REQUEST,
    )

    db_otp_hashed = (
        db.query(OTP)
        .join(models.User)
        .filter(
            models.User.id == urlsafe_b64decode(body.uid).decode(ENCODING),
            OTP.code == entered_otp_hashed,
        )
    ).first()

    if db_otp_hashed is None:
        return code_incorrect_response

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
    return JSONResponse(
        {"success": "The code you entered is correct. Email has been verified."},
        status.HTTP_200_OK,
    )
