from typing import Any

from dependencies import DatabaseDependency
from fastapi import APIRouter, HTTPException, status
from pydantic import IPvAnyAddress
from users.models import User

from . import crud, models, schemas

router = APIRouter()


@router.post("/modems/", response_model=schemas.ShowModem, status_code=status.HTTP_201_CREATED)
async def create_modem(request: schemas.CreateModem, db: DatabaseDependency) -> models.Modem:
    """
    Create modem or raise an exception if modem with provided IP is already exists.
    """
    db_modem = crud.get_modem_by_ip(db, str(request.ip))
    if db_modem is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Modem with the given IP is already exists.")

    bind_db_user = db.query(User).filter(User.email == request.bind_user_email).first()
    if bind_db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exist.")

    # must replace `bind_user_email` with `bind_user_id`, because `Modem` model does not have `bind_user_email` field
    modem_data: dict[str, Any] = request.model_dump(exclude={"bind_user_email"})
    modem_data["bind_user_id"] = bind_db_user.id

    return crud.create_modem(db, modem_data)


@router.get("/modems/{ip}", response_model=schemas.ShowModem, status_code=status.HTTP_200_OK)
async def get_modem(ip: IPvAnyAddress, db: DatabaseDependency) -> models.Modem:
    """
    Return a modem by its `ip`.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exist.")

    return db_modem


@router.get("/modems/", response_model=list[schemas.ShowModem], status_code=status.HTTP_200_OK)
async def get_all_modems(db: DatabaseDependency, skip: int = 0, limit: int = 100) -> list[models.Modem]:
    """
    Return all modems within `skip` and `limit` params.
    """
    return crud.get_all_modems(db, skip, limit)


@router.put("/modems/{ip}", response_model=schemas.ShowModem, status_code=status.HTTP_200_OK)
async def update_modem(ip: IPvAnyAddress, data: schemas.UpdateModem, db: DatabaseDependency) -> models.Modem:
    """
    Update modem by its IP address.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exists.")

    data_to_update: dict[str, Any] = data.model_dump()
    return crud.update_modem(db, db_modem, data_to_update)


@router.delete("/modems/{ip}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_modem(ip: IPvAnyAddress, db: DatabaseDependency) -> None:
    """
    Delete a modem with `ip`.
    """
    crud.delete_modem(db, str(ip))
