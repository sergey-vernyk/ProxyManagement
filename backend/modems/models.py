from datetime import datetime

from db_connection import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship


class Modem(Base):
    """
    Class represents LTE modem with assigned `ip` and `port`.
    `username` and `password` uses for getting access to the
    modem API.
    """

    __tablename__ = "modems"

    id = Column(Integer, primary_key=True)
    external_server_ip = Column(INET(), nullable=True)
    internal_server_ip = Column(INET(), nullable=True)
    external_server_port = Column(Integer, nullable=False, default=65000)
    external_server_host = Column(String(253), nullable=False, default="http://example.com")
    ip = Column(INET(), nullable=False)
    port = Column(Integer, nullable=False)
    bind_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    hashed_value = Column(String(32), nullable=True)
    username = Column(String(20), nullable=True)
    password = Column(String(20), nullable=True)
    rebooted = Column(DateTime(timezone=True), nullable=True, default=None)
    created = Column(DateTime(timezone=True), default=datetime.now, nullable=False)
    updated = Column(DateTime(timezone=True), onupdate=datetime.now, nullable=True, default=None)

    bind_user = relationship("User", back_populates="user_modems", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.ip}:{self.port} - {self.bind_user}"
