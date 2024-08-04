from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .db_connection import Base


class Modem(Base):
    """
    Class represents LTE modem with assigned IP and user.
    """

    __tablename__ = "modems"

    id = Column(Integer, primary_key=True)
    modem_ip = Column(String(16), nullable=False)
    token = Column(String(32), nullable=False)
    bind_user = relationship("User", back_populates="modems", lazy="selectin")
    bind_user_id = Column(Integer, ForeignKey("users.id"))
    modem_username = Column(String(20), nullable=True)
    modem_password = Column(String(20), nullable=True)
    reboot = Column(DateTime, nullable=True)
    create = Column(DateTime(timezone=True), default=datetime.now, nullable=False)
    update = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"{self.modem_ip}-{self.bind_user}"


class User(Base):
    """
    Class represents a user, who binds to a modem.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(50), unique=True, nullable=False)
    login = Column(String(20), nullable=False)
    password = Column(String(50), nullable=False)
    modems = relationship("Modem", back_populates="bind_user", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.email}"
