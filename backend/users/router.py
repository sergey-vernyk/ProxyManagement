import random
from secrets import token_urlsafe
from typing import Annotated, Any

from auth.auth_bearer import JWTBearer
from config import get_settings
from dependencies import DatabaseDependency
from fastapi import APIRouter, Depends, HTTPException, Query, status
from modems.crud import get_modem_by_ip
from pydantic import EmailStr, IPvAnyAddress
from security import (encrypt_modem_password, generate_md5_crypt_hash_password,
                      get_password_hash, verify_password)
from validators import validate_email_format

from . import crud, models, schemas

settings = get_settings()
ENCODING = settings.default_encoding

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
    request: schemas.CreateRegularUser | schemas.CreateAdminUser, db: DatabaseDependency
) -> models.User:
    """
    Create a user or raise an exception if user with provided email is already exists.
    """
    try:
        valid_email = validate_email_format(request.email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email is already registered.")

    token: str | None = None
    proxy_login: str | None = None
    proxy_password_hashed: str | None = None

    if isinstance(request, schemas.CreateRegularUser):
        token = token_urlsafe(32)[:32]
        proxy_login = token_urlsafe(32)[: random.randint(10, 20)]

        if request.proxy_password_hash_type is not None:
            if request.proxy_password_hash_type == schemas.HashType.MD5:
                proxy_password_hashed = generate_md5_crypt_hash_password(request.proxy_password_plain)
            else:
                proxy_password_hashed = encrypt_modem_password(
                    request.proxy_password_hash_type, request.proxy_password_plain
                )

    return crud.create_user(
        db,
        request,
        token,
        proxy_login,
        proxy_password_hashed,
    )


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
async def get_user(email: EmailStr, db: DatabaseDependency) -> models.User:
    """
    Returns a user by its `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
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
    ip: IPvAnyAddress, request: schemas.UpdateUserProxyCredentials, db: DatabaseDependency
) -> models.User:
    """
    Update user credentials for proxy.
    """
    db_modem = get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exists.")

    proxy_password: str | None = None

    if request.proxy_password_plain is not None and request.proxy_password_hash_type is not None:
        if request.proxy_password_hash_type == schemas.HashType.MD5:
            proxy_password = generate_md5_crypt_hash_password(request.proxy_password_plain)
        else:
            proxy_password = encrypt_modem_password(request.proxy_password_hash_type, request.proxy_password_plain)
    else:
        proxy_password = request.proxy_password_plain

    data_to_update = request.model_dump(exclude_unset=True, exclude={"password_hash_type", "update_login"})

    if "proxy_password" in data_to_update:
        data_to_update["proxy_password"] = proxy_password
    if request.update_login:
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
async def update_user(email: EmailStr, request: schemas.UpdateUser, db: DatabaseDependency) -> models.User:
    """
    Update user info with `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exists.")

    data_to_update: dict[str, Any] = {}

    if request.update_password and request.old_password is not None and request.new_password is not None:
        if not verify_password(request.old_password, str(db_user.hashed_password)):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Entered old password not matches with the existing user password."
            )
        data_to_update["hashed_password"] = get_password_hash(request.new_password)

    if request.update_token:
        token = token_urlsafe(32)[:32]
        data_to_update["token"] = token

    data_to_update["email"] = request.email

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
async def delete_user(email: EmailStr, db: DatabaseDependency) -> None:
    """
    Delete user with the given `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_user_by_email(db, valid_email)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email is not exists.")

    crud.delete_user(db, valid_email)
