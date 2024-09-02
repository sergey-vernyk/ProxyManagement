from security import get_password_hash
from sqlalchemy.orm import Session
from users.models import User

from .schemas import RegisterUser


def register_regular_user(db: Session, user_data: RegisterUser, token: str) -> None:
    """
    Create a regular user in the database.
    """

    user = User(email=user_data.email, hashed_password=get_password_hash(user_data.password), token=token)
    db.add(user)
    db.commit()
    db.refresh(user)
