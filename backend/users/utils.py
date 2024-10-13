from secrets import token_urlsafe

from auth.crud import register_regular_user_from_google
from config import get_settings
from sqlalchemy.orm import Session

settings = get_settings()


def create_user_from_google(email: str, db: Session) -> None:
    """
    Creates `User` instance from provided `email` while
    the user login in the system for the first time.

    Args:
        email (str): email of the user being created.
        db (Session): Database SQLAlchemy session.
    """
    user_unique_token = token_urlsafe(32)[: settings.unique_user_token_length]
    user = register_regular_user_from_google(db, email, user_unique_token)
    setattr(user, "is_verified", True)
