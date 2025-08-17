from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_connection import Base

if TYPE_CHECKING:
    from users.models import User


class OTP(Base):
    """Class represents one-time password `OTP`."""

    __tablename__ = "otp"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship("User", uselist=False, back_populates="user_otps", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.user}: {self.code}"

    @property
    def is_expired(self) -> bool:
        """Returns status of a code."""
        return bool(datetime.now() > self.expires_at)
