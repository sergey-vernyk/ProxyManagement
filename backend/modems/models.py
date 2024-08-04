from datetime import datetime

from db_connection import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class Modem(Base):
    """
    Class represents LTE modem with assigned IP and user.
    """

    __tablename__ = "modems"

    id = Column(Integer, primary_key=True)
    modem_ip = Column(String(16), nullable=False)
    token = Column(String(32), nullable=False)
    bind_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    modem_username = Column(String(20), nullable=True)
    modem_password = Column(String(20), nullable=True)
    rebooted = Column(DateTime(timezone=True), nullable=True)
    created = Column(DateTime(timezone=True), default=datetime.now, nullable=False)
    updated = Column(DateTime(timezone=True), onupdate=datetime.now, nullable=True)

    bind_user = relationship("User", back_populates="user_modems", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.modem_ip}-{self.bind_user}"
