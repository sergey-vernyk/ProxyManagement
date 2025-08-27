from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from proxy_management.db_connection import Base

from .schemas import HashType, UserRole

if TYPE_CHECKING:
    from ..auth.otp.models import OTP
    from ..modems.models import Modem


class UserAbstract(Base):
    """Abstract user class."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=True)
    role: Mapped[bool] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.REGULAR)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, nullable=False)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=datetime.now, nullable=True)


# pylint: disable=unsubscriptable-object
class User(UserAbstract):
    """Class represents a user, who binds to a modem(s)."""

    __tablename__ = "users"

    token: Mapped[str] = mapped_column(String(32), nullable=True)
    proxy_login: Mapped[str] = mapped_column(String(20), nullable=True)
    proxy_password_plain: Mapped[str] = mapped_column(String(20), nullable=True)
    proxy_password_hashed: Mapped[str] = mapped_column(String(64), nullable=True)
    proxy_password_hash_type: Mapped[str] = mapped_column(Enum(HashType), nullable=True)

    user_modems: Mapped[list["Modem"]] = relationship("Modem", back_populates="bind_user", lazy="selectin")
    user_otps: Mapped[list["OTP"]] = relationship("OTP", uselist=True, back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.email}"
