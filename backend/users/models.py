from db_connection import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship


class User(Base):
    """
    Class represents a user, who binds to a modem.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(50), unique=True, nullable=False)
    login = Column(String(20), nullable=False)
    password = Column(String(50), nullable=False)

    user_modems = relationship("Modem", back_populates="bind_user", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.email}"
