from sqlalchemy.orm import Session

from .db_connection import SessionLocal


def get_db():
    """
    Creates a new SQLAlchemy Session instance
    that will be used in a single request.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
