import hashlib
import selectors
import socket
from typing import Any, TypeAlias

from config import get_settings
from dependencies import DatabaseDependency
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import IPvAnyAddress
from sockets import multiconn_client
from users.models import User

from . import crud, models, schemas

settings = get_settings()


router = APIRouter()

Socket: TypeAlias = socket.socket
Selector: TypeAlias = selectors.DefaultSelector

SOCKET_HOST: str = settings.socket_host
SOCKET_PORT: int = settings.socket_port

socket_obj: Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sel: Selector = selectors.DefaultSelector()


def send_data_to_socket_server(data_to_send: str, socket_host: str, socket_port: int, selector: Selector) -> None:
    """
    The function creates socket client
    and sends the given `data_to_send` data to the socket server.
    """
    with multiconn_client.SocketClient(socket_host, socket_port, socket_obj, selector) as client:
        client.compose_data_to_send(data_to_send)
        client.run_event_loop()


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
    modem_data["hashed_value"] = hashlib.sha256(f"{bind_db_user.email}".encode("utf-8")).hexdigest()[::2]

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


@router.get(
    "/modems/{token}/{hashed_value}",
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    responses={
        200: {"description": "IP changed"},
        404: {"description": "Modem not Found"},
        400: {"description": "Incorrect token or hash value"},
        406: {"description": "Problems on socket server side"},
    },
)
async def change_ip(token: str, hashed_value: str, db: DatabaseDependency) -> JSONResponse:
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
    port = str(modem.port)
    username = str(modem.username)
    password = str(modem.password)
    data_to_send: str = ",".join([ip, port, username, password])
    send_data_to_socket_server(data_to_send, SOCKET_HOST, SOCKET_PORT, sel)

    return JSONResponse(
        {"ip": ip, "port": port, "username": username, "password": password}, status_code=status.HTTP_200_OK
    )
