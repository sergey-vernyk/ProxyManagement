from typing import Any

from security import get_password_hash
from sqlalchemy.orm import Session

from . import models, schemas


def create_regular_user(
    db: Session, user_data: schemas.CreateRegularUser, token: str, proxy_login: str, proxy_password: str
) -> models.RegularUser:
    """
    Creates regular user in the database.
    """
    user_data = models.RegularUser(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        proxy_login=proxy_login,
        token=token,
        proxy_password=proxy_password,
    )
    db.add(user_data)
    db.commit()
    db.refresh(user_data)
    return user_data


def create_admin_user(db: Session, user_data: schemas.CreateAdminUser) -> models.AdminUser:
    """
    Creates admin user in the database.
    """
    user_data = models.AdminUser(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(user_data)
    db.commit()
    db.refresh(user_data)
    return user_data


def get_user_by_id(db: Session, user_id: int) -> models.RegularUser | None:
    """
    Returns user by given ID.
    """
    return db.query(models.RegularUser).filter(models.RegularUser.id == user_id).first()


def get_regular_user_by_email(db: Session, email: str) -> models.RegularUser | None:
    """
    Returns a regular user by given `email`.
    """
    return db.query(models.RegularUser).filter(models.RegularUser.email == email).first()


def get_admin_user_by_email(db: Session, email: str) -> models.AdminUser | None:
    """
    Returns an admin user by the given `email`.
    """
    return db.query(models.AdminUser).filter(models.AdminUser.email == email).first()


def get_regular_users(db: Session, offset: int = 0, limit: int = 100) -> list[models.RegularUser]:
    """
    Returns all regular users within `offset` and `limit`.
    """
    return db.query(models.RegularUser).offset(offset).limit(limit).all()


def update_user_info(db: Session, instance: models.RegularUser, data_to_update: dict[Any, Any]) -> models.RegularUser:
    """
    Update user by its ID.
    """
    db.query(models.RegularUser).filter(models.RegularUser.id == instance.id).update(data_to_update)
    db.commit()
    db.refresh(instance)
    return instance


def update_user_proxy_credentials(
    db: Session, instance: models.RegularUser, data_to_update: dict[Any, Any]
) -> models.RegularUser:
    """
    Update proxy credentials for the given `instance`.
    """
    db.query(models.RegularUser).filter(models.RegularUser.id == instance.id).update(data_to_update)
    db.commit()
    db.refresh(instance)
    return instance


def delete_user(db: Session, email: str) -> None:
    """
    Remove user with `user_email` from database.
    """
    db.query(models.RegularUser).filter(models.RegularUser.email == email).delete()
    db.commit()
