from dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import crud, models, schemas

router = APIRouter()


@router.post("/users/", response_model=schemas.UserShow, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.CreateUser, db: Session = Depends(get_db)) -> models.User:
    """
    Create user or raise an exception if user with provided email is already exists.
    """
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with given email is already registered.")

    user = crud.create_user(db, user)
    return user


@router.get("/users/", response_model=list[schemas.UserShow], status_code=status.HTTP_200_OK)
async def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[models.User]:
    """
    Returns all users within `skip` and `limit` params.
    """
    return crud.get_all_users(db, offset=skip, limit=limit)
