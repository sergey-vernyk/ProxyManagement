import datetime
import hashlib
import selectors
import socket
from typing import Annotated, Any, TypeAlias

from config import get_settings
from conn_utils import build_default_route_ip, send_data_to_socket_server
from dependencies import DatabaseDependency
from fastapi import APIRouter, HTTPException, Path, status
from fastapi.responses import JSONResponse
from pydantic import IPvAnyAddress
from users.models import User

from . import crud, models, schemas

settings = get_settings()

router = APIRouter()

Socket: TypeAlias = socket.socket
Selector: TypeAlias = selectors.DefaultSelector

SOCKET_HOST: str = settings.socket_host
SOCKET_PORT: int = settings.socket_port
ENCODING: str = settings.default_encoding


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
    modem_data: dict[str, Any] = request.model_dump(exclude={"bind_user_email", "ip"})
    modem_data["bind_user_id"] = bind_db_user.id
    modem_data["ip"] = str(request.ip)
    modem_data["hashed_value"] = hashlib.sha256(f"{bind_db_user.email}{modem_data['ip']}".encode(ENCODING)).hexdigest()[
        ::2
    ]

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

    data_to_update: dict[str, Any] = data.model_dump(exclude={"ip"})
    data_to_update["ip"] = str(data.ip)
    return crud.update_modem(db, db_modem, data_to_update)


@router.delete("/modems/{ip}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_modem(ip: IPvAnyAddress, db: DatabaseDependency) -> None:
    """
    Delete a modem with `ip`.
    """
    crud.delete_modem(db, str(ip))


@router.get(
    "/modems/{token}/{hashed_value}",
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={
        200: {"description": "IP changed"},
        404: {"description": "Modem not Found"},
        406: {"description": ["Problems on socket server side", "Problems on modem side"]},
    },
)
async def change_ip(
    token: Annotated[str, Path(max_length=32, description="User token")],
    hashed_value: Annotated[str, Path(max_length=32, description="Modem hashed value")],
    db: DatabaseDependency,
) -> JSONResponse:
    """
    Change IP of a modem.
    - token (str): token from user data.
    - hashed_value (str): hashed value from modem data, which bind to that modem.
    - db: (DatabaseDependency): database session.
    """
    modem = (
        db.query(models.Modem).join(User).filter(models.Modem.hashed_value == hashed_value, User.token == token).first()
    )
    if modem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requested modem is not found. Check token or hashed value.")

    ip = str(modem.ip)
    username = str(modem.username)
    password = str(modem.password)
    default_route: str = build_default_route_ip(ip)

    socket_obj: Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sel: Selector = selectors.DefaultSelector()

    data_to_send: str = ",".join([default_route, username, password])
    received_data = send_data_to_socket_server(data_to_send, SOCKET_HOST, SOCKET_PORT, socket_obj, sel)
    if received_data is not None:
        str_recv_data: str = received_data.decode(ENCODING)
        if received_data == b"Rebooted":
            setattr(modem, "rebooted", datetime.datetime.now())
            db.commit()
            return JSONResponse({"message": "Modem rebooted successfully."}, status.HTTP_200_OK)
        if received_data == b"Not rebooted":
            return JSONResponse({"message": "Modem not rebooted. Try again."}, status.HTTP_200_OK)
        if b"Error" in received_data:
            return JSONResponse({"message": f"Modem side error:{str_recv_data[6:]}"}, status.HTTP_406_NOT_ACCEPTABLE)
        if b"Errno" in received_data:
            return JSONResponse({"message": f"Server side error: {str_recv_data}"}, status.HTTP_406_NOT_ACCEPTABLE)

    return JSONResponse({"message": "No data received from the server."}, status.HTTP_200_OK)
