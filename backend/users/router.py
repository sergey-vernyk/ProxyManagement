import random
from secrets import token_urlsafe

from auth.auth_bearer import JWTBearer
from config import get_settings
from dependencies import DatabaseDependency
from fastapi import APIRouter, Depends, HTTPException, status
from modems.crud import get_modem_by_ip
from pydantic import EmailStr, IPvAnyAddress
from security import encrypt_modem_password
from validators import validate_email_format

from . import crud, models, schemas

settings = get_settings()
ENCODING = settings.default_encoding

router = APIRouter()


@router.post(
    "/users/",
    tags=["regular-users"],
    response_model=schemas.ShowRegularUser,
    status_code=status.HTTP_201_CREATED,
    description="Create a regular user for a modem.",
    dependencies=[Depends(JWTBearer())],
    operation_id="create-regular-user",
    responses={
        201: {"description": "User created"},
        400: {"description": "User already registered or invalid email format"},
    },
)
async def create_regular_user(request: schemas.CreateRegularUser, db: DatabaseDependency) -> models.RegularUser:
    """
    Create a regular user or raise an exception if user with provided email is already exists.
    """
    try:
        valid_email = validate_email_format(request.email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_regular_user_by_email(db, valid_email)
    if db_user is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email is already registered.")

    token: str = token_urlsafe(32)[:32]
    proxy_login: str = token_urlsafe(32)[: random.randint(10, 20)]
    proxy_password: str

    if request.proxy_password_hash_type is not None:
        proxy_password: str = encrypt_modem_password(request.proxy_password_hash_type, request.proxy_password)
    else:
        proxy_password: str = request.proxy_password

    return crud.create_regular_user(db, request, token, proxy_login, proxy_password)


@router.post(
    "/users/admin/",
    tags=["admin-users"],
    response_model=schemas.ShowAdminUser,
    status_code=status.HTTP_201_CREATED,
    description="Create admin user.",
    operation_id="create-admin-user",
    responses={
        201: {"description": "User created"},
        400: {"description": "User already registered or invalid email format"},
    },
)
async def create_admin_user(request: schemas.CreateAdminUser, db: DatabaseDependency) -> models.AdminUser:
    """
    Create a regular user or raise an exception if user with provided email is already exists.
    """
    try:
        valid_email = validate_email_format(request.email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_admin_user_by_email(db, valid_email)
    if db_user is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email is already registered.")

    return crud.create_admin_user(db, request)


@router.get(
    "/users/",
    tags=["regular-users"],
    response_model=list[schemas.ShowRegularUser],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Get all regular users within `skip` and `limit` params.",
    operation_id="get-regular-users",
    responses={200: {"description": "Successfully"}},
)
async def get_regular_users(db: DatabaseDependency, skip: int = 0, limit: int = 100) -> list[models.RegularUser]:
    """
    Returns all regular users within `skip` and `limit` params.
    """
    return crud.get_regular_users(db, offset=skip, limit=limit)


@router.get(
    "/users/{email}",
    tags=["regular-users"],
    response_model=schemas.ShowRegularUser,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Get a regular user by the given email.",
    operation_id="get-regular-user-by-email",
    responses={
        404: {"description": "User not found"},
        400: {"description": "Invalid email format"},
        200: {"description": "Successfully"},
    },
)
async def get_regular_user(email: EmailStr, db: DatabaseDependency) -> models.RegularUser:
    """
    Returns a user by its `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_regular_user_by_email(db, valid_email)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exist.")

    return db_user


@router.patch(
    "/users/proxy/{ip}",
    tags=["regular-users"],
    response_model=schemas.ShowRegularUser,
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
) -> models.RegularUser:
    """
    Update user credentials for proxy.
    """
    db_modem = get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exists.")

    proxy_password: str

    if request.proxy_password is not None:
        if request.proxy_password_hash_type is not None:
            proxy_password: str = encrypt_modem_password(request.proxy_password_hash_type, request.proxy_password)
        else:
            proxy_password = request.proxy_password

    data_to_update = request.model_dump(exclude_unset=True, exclude={"password_hash_type", "update_login"})

    if "proxy_password" in data_to_update:
        data_to_update["proxy_password"] = proxy_password
    if request.update_login:
        data_to_update["proxy_login"] = token_urlsafe(32)[: random.randint(10, 20)]

    return crud.update_user_proxy_credentials(db, db_modem.bind_user, data_to_update)


@router.put(
    "/users/{email}",
    tags=["regular-users"],
    response_model=schemas.ShowRegularUser,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Update a regular user by the given email.",
    operation_id="update-regular-user",
    responses={
        404: {"description": "User not found"},
        400: {"description": "Invalid email format"},
        200: {"description": "Successfully"},
    },
)
async def update_regular_user(
    email: EmailStr, request: schemas.UpdateRegularUser, db: DatabaseDependency
) -> models.RegularUser:
    """
    Update user info with `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_regular_user_by_email(db, valid_email)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exists.")

    return crud.update_user_info(db, db_user, request.model_dump())


@router.delete(
    "/users/{email}",
    tags=["regular-users"],
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete a regular user by the given email.",
    dependencies=[Depends(JWTBearer())],
    operation_id="delete-regular-user-by-email",
    responses={
        400: {"description": "Invalid email format"},
        404: {"description": "User not found"},
        200: {"description": "Successfully"},
    },
)
async def delete_regular_user(email: EmailStr, db: DatabaseDependency) -> None:
    """
    Delete user with the given `email`.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = crud.get_regular_user_by_email(db, valid_email)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email is not exists.")

    crud.delete_user(db, valid_email)
