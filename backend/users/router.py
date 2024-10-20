"""
Module contains endpoints for users:
- create_user
- get_user
- get_users
- update_user
- delete_user
"""

import random
from secrets import token_urlsafe
from typing import Annotated, Any

from auth.otp.utils import send_otp_email_handler
from config import get_settings
from dependencies import DatabaseDependency, jwt_verification
from exceptions import ClientRequestError, EntityDoesNotExistError
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from logs.logging_conf import build_logger_extra_data, get_endpoint_logger
from pydantic import EmailStr
from security import (encrypt_modem_password, generate_md5_crypt_hash_password,
                      get_password_hash, verify_password)
from validators import validate_email_format

from . import crud, models, schemas

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
    try:
        valid_email = validate_email_format(body.email)
    except ValueError as e:
        raise ClientRequestError(
            f"Email is invalid. Reason: {e}.",
            logger_extra_data=build_logger_extra_data(request),
        ) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is not None:
        raise ClientRequestError(
            "User with the given email is already registered.",
            logger_extra_data=build_logger_extra_data(request),
        )

    token: str | None = None
    proxy_login: str | None = None
    proxy_password_hashed: str | None = None

    if isinstance(body, schemas.CreateRegularUser):
        token = token_urlsafe(32)[: settings.unique_user_token_length]
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

    await send_otp_email_handler(bg_tasks, request, str(user.token), db)
    return user


@router.get(
    "/users/",
    response_model=list[schemas.ShowUser],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(jwt_verification)],
    description="Get all users within `skip` and `limit` params.",
    operation_id="get-users",
    responses={200: {"description": "Successfully"}},
)
async def get_users(
    db: DatabaseDependency,
    user_type: Annotated[str, Query(description="Type of user: admin or regular.", default="regular")] | None = None,
    is_verified: Annotated[
        bool,
        Query(
            description="Get users who are either verified, not verified their email or all users.",
        ),
    ] = True,
    skip: int = 0,
    limit: int = 100,
) -> list[models.User]:
    """
    Returns all users between `skip` and `limit` that are `admin`, `regular`, or any of them.
    """
    return crud.get_users(db, user_type, is_verified, offset=skip, limit=limit)


@router.get(
    "/users/{email}",
    response_model=schemas.ShowUser,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(jwt_verification)],
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
        raise ClientRequestError(
            f"Email is invalid. Reason: {e}.",
            logger_extra_data=build_logger_extra_data(request),
        ) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
        raise EntityDoesNotExistError(
            message="User with the given email does not exist.",
            logger_extra_data=build_logger_extra_data(request),
        )

    return db_user


@router.put(
    "/users/{email}",
    response_model=schemas.ShowUser,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(jwt_verification)],
    description="Update a user by the given email.",
    operation_id="update-user",
    responses={
        404: {"description": "User not found"},
        400: {"description": "Invalid email format or passwords mismatch or proxy password hash type is not provided."},
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
        raise ClientRequestError(
            f"Email is invalid. Reason: {e}.",
            logger_extra_data=build_logger_extra_data(request),
        ) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
        raise EntityDoesNotExistError(
            "User with the given email does not exist",
            logger_extra_data=build_logger_extra_data(request),
        )

    data_to_update: dict[str, Any] = {}

    if body.update_password and body.old_password is not None and body.new_password is not None:
        if not verify_password(body.old_password, str(db_user.hashed_password)):
            raise ClientRequestError(
                "Entered old password not matches with the existing user password.",
                logger_extra_data=build_logger_extra_data(request),
            )

        data_to_update["hashed_password"] = get_password_hash(body.new_password)

    if body.update_token:
        data_to_update["token"] = token_urlsafe(32)[: settings.unique_user_token_length]

    if body.update_proxy_login:
        proxy_login = token_urlsafe(32)[: random.randint(10, 20)]
        data_to_update["proxy_login"] = proxy_login

    proxy_password_hashed: str | None = None
    if body.update_proxy_password and body.proxy_password_plain is not None:
        if body.proxy_password_hash_type is None:
            raise ClientRequestError(
                "Proxy password hash type must not be None if password to update is provided.",
                logger_extra_data=build_logger_extra_data(request),
            )

        if body.proxy_password_hash_type == schemas.HashType.MD5:
            proxy_password_hashed = generate_md5_crypt_hash_password(body.proxy_password_plain)
        else:
            proxy_password_hashed = encrypt_modem_password(body.proxy_password_hash_type, body.proxy_password_plain)

        data_to_update["proxy_password_plain"] = body.proxy_password_plain
        data_to_update["proxy_password_hashed"] = proxy_password_hashed
        data_to_update["proxy_password_hash_type"] = body.proxy_password_hash_type

    data_to_update["email"] = body.email

    return crud.update_user_info(db, db_user, data_to_update)


@router.delete(
    "/users/{email}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete a user by the given email.",
    dependencies=[Depends(jwt_verification)],
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
        raise ClientRequestError(
            f"Email is invalid. Reason: {e}.",
            logger_extra_data=build_logger_extra_data(request),
        ) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
        raise EntityDoesNotExistError(
            "User with the given email does not exist",
            logger_extra_data=build_logger_extra_data(request),
        )

    crud.delete_user(db, valid_email)
