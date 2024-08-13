from typing import Any

from sqlalchemy.orm import Session
from users.models import User

from . import models


def create_modem(db: Session, modem_data: dict[str, Any]) -> models.Modem:
    """
    Create modem with provided attributes in the database.
    """
    modem = models.Modem(
        ip=modem_data.get("ip"),
        port=modem_data.get("port"),
        bind_user_id=modem_data.get("bind_user_id"),
        hashed_value=modem_data.get("hashed_value"),
        username=modem_data.get("username"),
        password=modem_data.get("password"),
    )
    db.add(modem)
    db.commit()
    db.refresh(modem)
    return modem


def update_modem(db: Session, instance: models.Modem, data_to_update: dict[Any, Any]) -> models.Modem:
    """
    Updates modem `instance` with `data_to_update`.
    """
    db.query(models.Modem).filter(models.Modem.id == instance.id).update(data_to_update)
    db.commit()
    db.refresh(instance)
    return instance


def get_all_modems(db: Session, skip: int = 0, limit: int = 100) -> list[models.Modem]:
    """
    Returns all modems within `offset` and `limit`.
    """
    return db.query(models.Modem).offset(skip).limit(limit).all()


def get_modem_by_ip(db: Session, ip: str) -> models.Modem | None:
    """
    Returns modem by the given `ip`.
    """
    return db.query(models.Modem).filter(models.Modem.ip == ip).first()


def get_modems_by_bind_user_email(db: Session, email: str) -> list[models.Modem]:
    """
    Returns modems by the given `email` of the bind user.
    """
    return db.query(models.Modem).join(User).filter(User.email == email).all()


def delete_modem(db: Session, ip: str) -> None:
    """
    Delete modem with `ip` from database.
    """
    db.query(models.Modem).filter(models.Modem.ip == ip).delete()
    db.commit()
