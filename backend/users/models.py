from datetime import datetime

from db_connection import Base
from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship

from .schemas import HashType, UserRole


class UserAbstract(Base):
    """
    Abstract user class.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True)
    email = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.REGULAR)
    created = Column(DateTime(timezone=True), default=datetime.now, nullable=False)
    updated = Column(DateTime(timezone=True), onupdate=datetime.now, nullable=True)


class AdminUser(UserAbstract):
    """
    Class represents user with the admin role.
    The user has more access than regular user.
    """

    __tablename__ = "admins"

    role = Column(Enum(UserRole), nullable=False, default=UserRole.ADMIN)


class RegularUser(UserAbstract):
    """
    Class represents a regular user, who binds to a modem(s).
    """

    __tablename__ = "users"

    token = Column(String(32), nullable=False)
    proxy_login = Column(String(20), nullable=False)
    proxy_password = Column(String(64), nullable=False)
    proxy_password_hash_type = Column(Enum(HashType), nullable=False, default=HashType.MD5)

    user_modems = relationship("Modem", back_populates="bind_user", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.email}"
