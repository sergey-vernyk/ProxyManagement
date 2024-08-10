from typing import Any

from sqlalchemy.orm import Session

from . import models, schemas


def create_user(
    db: Session, user_data: schemas.CreateUser, token: str, proxy_login: str, proxy_password: str
) -> models.User:
    """
    Creates user in the database.
    """
    user_data = models.User(
        email=user_data.email,
        proxy_login=proxy_login,
        token=token,
        proxy_password=proxy_password,
    )
    db.add(user_data)
    db.commit()
    db.refresh(user_data)
    return user_data


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    """
    Returns user by given ID.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> models.User | None:
    """
    Returns user by given `email`.
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_all_users(db: Session, offset: int = 0, limit: int = 100) -> list[models.User]:
    """
    Returns all users within `offset` and `limit`.
    """
    return db.query(models.User).offset(offset).limit(limit).all()


def update_user_info(db: Session, instance: models.User, data_to_update: dict[Any, Any]) -> models.User:
    """
    Update user by its ID.
    """
    db.query(models.User).filter(models.User.id == instance.id).update(data_to_update)
    db.commit()
    db.refresh(instance)
    return instance


def update_user_proxy_credentials(db: Session, instance: models.User, data_to_update: dict[Any, Any]) -> models.User:
    """
    Update proxy credentials for the given `instance`.
    """
    db.query(models.User).filter(models.User.id == instance.id).update(data_to_update)
    db.commit()
    db.refresh(instance)
    return instance


def delete_user(db: Session, email: str) -> None:
    """
    Remove user with `user_email` from database.
    """
    db.query(models.User).filter(models.User.email == email).delete()
    db.commit()
