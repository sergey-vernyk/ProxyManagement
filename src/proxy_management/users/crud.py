from typing import Any

from sqlalchemy.orm import Session

from proxy_management.security import get_password_hash

from . import models, schemas


def create_user(
    db: Session,
    user_data: schemas.CreateRegularUser | schemas.CreateAdminUser,
    token: str | None,
    proxy_login: str | None,
    proxy_password_hashed: str | None,
) -> models.User:
    """Create a user in the database."""
    is_regular = isinstance(user_data, schemas.CreateRegularUser)

    user = models.User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        proxy_login=proxy_login if is_regular else None,
        proxy_password_plain=user_data.proxy_password_plain if is_regular else None,
        proxy_password_hashed=proxy_password_hashed if is_regular else None,
        proxy_password_hash_type=user_data.proxy_password_hash_type if is_regular else None,
        token=token if is_regular else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    """Returns user by given ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Returns a user by given `email`."""
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(
    db: Session, user_type: str | None, is_verified: bool = True, offset: int = 0, limit: int = 100
) -> list[models.User]:
    """
    Returns users with the params

    Args:
        db (Session): database session.
        user_type (str | None): type of users who will be get: regular or admin.
        is_verified (bool, optional): users who are verified their email or not verified. Defaults to True.
        offset (int, optional): skip records from the start of results. Defaults to 0.
        limit (int, optional): number of records to get from all select condition. Defaults to 100.

    Returns:
        list[models.User]: list of the users corresponding to the params above.
    """
    if user_type is not None:
        return (
            db.query(models.User)
            .filter(models.User.role == user_type, models.User.is_verified == is_verified)
            .offset(offset)
            .limit(limit)
            .all()
        )

    return db.query(models.User).filter(models.User.is_verified == is_verified).offset(offset).limit(limit).all()


def update_user_info(db: Session, instance: models.User, data_to_update: dict[Any, Any]) -> models.User:
    """Update user by its ID."""
    db.query(models.User).filter(models.User.id == instance.id).update(data_to_update)
    db.commit()
    db.refresh(instance)
    return instance


def delete_user(db: Session, email: str) -> None:
    """Remove user with `user_email` from database."""
    db.query(models.User).filter(models.User.email == email).delete()
    db.commit()
