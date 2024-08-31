from datetime import datetime

from db_connection import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class OTP(Base):
    """
    Class represents one-time password OTP.
    """

    __tablename__ = "otp"

    id = Column(Integer, primary_key=True, unique=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now())
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="user_otps", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.user}: {self.code}"

    @property
    def is_expired(self) -> bool:
        """
        Returns status of a code.
        """
        return bool(datetime.now() > self.expires_at)
