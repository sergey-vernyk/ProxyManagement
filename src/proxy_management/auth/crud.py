from sqlalchemy.orm import Session

from ..security import get_password_hash
from ..users.models import User
from .schemas import RegisterUser


def register_regular_user(db: Session, user_data: RegisterUser, token: str) -> None:
    """Create a regular user in the database."""
    user = User(email=user_data.email, hashed_password=get_password_hash(user_data.password), token=token)
    db.add(user)
    db.commit()
    db.refresh(user)


def register_regular_user_from_google(db: Session, email: str, token: str) -> User:
    """
    Create a regular user in the database,
    if the user login via Google Oauth2 for the first time.
    """
    user = User(email=email, token=token)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
