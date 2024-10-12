from secrets import token_urlsafe

from auth.crud import register_regular_user_from_google
from sqlalchemy.orm import Session


def create_user_from_google(email: str, db: Session) -> None:
    user_unique_token = token_urlsafe(32)[:32]
    user = register_regular_user_from_google(db, email, user_unique_token)
    setattr(user, "is_verified", True)
