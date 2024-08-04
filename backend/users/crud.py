from sqlalchemy.orm import Session

from . import models, schemas


def create_user(db: Session, user: schemas.CreateUser) -> models.User:
    """
    Creates user in the database.
    """
    user = models.User(email=user.email, login=user.login, password=user.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> models.User:
    """
    Returns user by given ID.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> models.User:
    """
    Returns user by given email.
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_all_users(db: Session, offset: int = 0, limit: int = 100) -> list[models.User]:
    """
    Returns all users within `offset` and `limit`.
    """
    return db.query(models.User).offset(offset).limit(limit).all()
