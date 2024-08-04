from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from .db_connection import Base


class Modem(Base):
    """
    Class represents LTE modem with assigned IP and user.
    """

    __tablename__ = "modems"

    id = Column(Integer, primary_key=True)
    modem_ip = Column(String(16), nullable=False)
    token = Column(String(32), nullable=False)
    bind_user = Column(String(50), unique=True, nullable=False)
    modem_username = Column(String(20), nullable=True)
    modem_password = Column(String(20), nullable=True)
    reboot = Column(DateTime, nullable=True)
    create = Column(DateTime(timezone=True), default=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"{self.modem_ip}-{self.bind_user}"
