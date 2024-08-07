import random
from secrets import token_urlsafe

from dependencies import DatabaseDependency
from fastapi import APIRouter, HTTPException, status
from validators import validate_email_format

from . import crud, models, schemas

router = APIRouter()


@router.post("/users/", response_model=schemas.ShowUser, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.CreateUser, db: DatabaseDependency) -> models.User:
    """
    Create user or raise an exception if user with provided email is already exists.
    """
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email is already registered.")

    token = token_urlsafe(32)[:32]
    password = token_urlsafe(32)[: random.randint(12, 20)]
    user = crud.create_user(db, user, token, password)
    return user


@router.get("/users/", response_model=list[schemas.ShowUser], status_code=status.HTTP_200_OK)
async def get_all_users(db: DatabaseDependency, skip: int = 0, limit: int = 100) -> list[models.User]:
    """
    Returns all users within `skip` and `limit` params.
    """
    return crud.get_all_users(db, offset=skip, limit=limit)


@router.get("/users/{email}", response_model=schemas.ShowUser, status_code=status.HTTP_200_OK)
async def get_user(email: str, db: DatabaseDependency) -> models.User:
    """
    Returns a user by its `email`.
    """
    if validate_email_format(email) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid email format.")

    db_user = crud.get_user_by_email(db, email)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exist.")

    return db_user


@router.put("/users/{email}", response_model=schemas.ShowUser, status_code=status.HTTP_200_OK)
async def update_user_proxy_credentials(
    email: str, data: schemas.UpdateUserCredentials, db: DatabaseDependency
) -> models.User:
    """
    Update user credentials for proxy.
    """
    if validate_email_format(email) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid email format.")

    db_user = crud.get_user_by_email(db, email)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email is not exists.")

    data_to_update = data.model_dump()
    return crud.update_user_proxy_credentials(db, db_user, data_to_update)


@router.delete("/users/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(email: str, db: DatabaseDependency) -> None:
    """
    Delete user with the given `email`.
    """
    if validate_email_format(email) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid email format.")

    crud.delete_user(db, email)
