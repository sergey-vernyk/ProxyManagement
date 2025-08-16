from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_connection import Base

if TYPE_CHECKING:
    from users.models import User


class Modem(Base):
    """
    Class represents LTE modem with assigned `ip` and `port`.
    `username` and `password` used for getting access to the
    modem API.
    """

    __tablename__ = "modems"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_server_ip: Mapped[str] = mapped_column(INET(), nullable=True)
    internal_server_ip: Mapped[str] = mapped_column(INET(), nullable=True)
    external_server_port: Mapped[int] = mapped_column(nullable=False, default=65000)
    external_server_host: Mapped[str] = mapped_column(String(253), nullable=False, default="http://example.com")
    ip: Mapped[str] = mapped_column(INET(), nullable=False)
    port: Mapped[int] = mapped_column(nullable=False)
    bind_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    hashed_value: Mapped[str] = mapped_column(String(32), nullable=True)
    username: Mapped[str] = mapped_column(String(20), nullable=True)
    password: Mapped[str] = mapped_column(String(20), nullable=True)
    rebooted: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, nullable=False)
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=datetime.now, nullable=True, default=None
    )

    bind_user: Mapped["User"] = relationship("User", uselist=False, back_populates="user_modems", lazy="selectin")

    def __repr__(self) -> str:
        return f"{self.ip}:{self.port} - {self.bind_user}"
