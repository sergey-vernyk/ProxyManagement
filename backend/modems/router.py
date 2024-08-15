import datetime
import hashlib
import selectors
import socket
from ipaddress import IPv4Address
from typing import Annotated, Any, TypeAlias

from auth.auth_bearer import JWTBearer
from config import get_settings
from conn_utils import build_default_route_ip, send_data_to_socket_server
from dependencies import DatabaseDependency
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import EmailStr, IPvAnyAddress
from pydantic_core import Url
from users.crud import get_user_by_email
from users.models import User
from validators import validate_email_format

from . import crud, models, schemas

settings = get_settings()

router = APIRouter()

Socket: TypeAlias = socket.socket
Selector: TypeAlias = selectors.DefaultSelector

SOCKET_HOST: str = settings.socket_host
SOCKET_PORT: int = settings.socket_port
ENCODING: str = settings.default_encoding


@router.post(
    "/modems/",
    response_model=schemas.ShowModem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(JWTBearer())],
    description="Create a modem for a proxy.",
    operation_id="create-modem",
    responses={
        201: {"description": "Modem created"},
        400: {"description": "Modem exists"},
        404: {"description": "User not found"},
    },
)
async def create_modem(request: schemas.CreateModem, db: DatabaseDependency) -> schemas.ShowModem:
    """
    Create modem or raise an exception if modem with provided IP is already exists.
    """
    db_modem = crud.get_modem_by_ip(db, str(request.ip))
    if db_modem is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Modem with the given IP is already exists.")

    bind_db_user: User | None = None
    if request.bind_user_email is not None:
        bind_db_user = db.query(User).filter(User.email == request.bind_user_email).first()
        if bind_db_user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exist.")

    modem_data: dict[str, Any] = request.model_dump(exclude={"bind_user_email", "ip", "public_server_ip"})
    modem_data["bind_user_id"] = bind_db_user.id if bind_db_user is not None else None
    modem_data["ip"] = str(request.ip)
    modem_data["public_server_ip"] = str(request.public_server_ip) if request.public_server_ip is not None else None

    if bind_db_user is not None:
        modem_data["hashed_value"] = hashlib.sha256(
            f"{bind_db_user.email}{modem_data['ip']}".encode(ENCODING)
        ).hexdigest()[::2]

    modem = crud.create_modem(db, modem_data)
    show_modem = schemas.ShowModem(
        **jsonable_encoder(modem, exclude={"bind_user"}),
        bind_user_email=str(bind_db_user.email) if bind_db_user is not None else None,
    )

    return show_modem


@router.get(
    "/modems/{ip}",
    response_model=schemas.ShowModem,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Get modem by the given IP.",
    operation_id="get-modem-by-ip",
    responses={
        200: {"description": "Successfully"},
        404: {"description": "Modem not found"},
    },
)
async def get_modem(ip: IPvAnyAddress, db: DatabaseDependency) -> schemas.ShowModem:
    """
    Return a modem by its `ip`.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exist.")

    show_modem = schemas.ShowModem(
        **jsonable_encoder(db_modem),
        bind_user_email=str(db_modem.bind_user.email) if db_modem.bind_user is not None else None,
    )
    return show_modem


@router.get(
    "/modems/",
    response_model=list[schemas.ShowModem],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Get all modems within `skip` and `limit` params.",
    operation_id="get-modems",
    responses={200: {"description": "Successfully"}},
)
async def get_all_modems(db: DatabaseDependency, skip: int = 0, limit: int = 100) -> list[schemas.ShowModem]:
    """
    Return all modems within `skip` and `limit` params.
    """
    modems = crud.get_all_modems(db, skip, limit)
    return [
        schemas.ShowModem(
            **jsonable_encoder(modem),
            bind_user_email=str(modem.bind_user.email) if modem.bind_user is not None else None,
        )
        for modem in modems
    ]


@router.put(
    "/modems/{ip}",
    response_model=schemas.ShowModem,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(JWTBearer())],
    description="Update a  modem data by the given IP.",
    responses={404: {"description": "Modem not found"}, 200: {"description": "Successfully"}},
)
async def update_modem(ip: IPvAnyAddress, request: schemas.UpdateModem, db: DatabaseDependency) -> schemas.ShowModem:
    """
    Update modem by its IP address.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exists.")

    bind_db_user: User | None = None
    if request.bind_user_email is not None:
        bind_db_user = db.query(User).filter(User.email == request.bind_user_email).first()
        if bind_db_user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exists.")

    data_to_update: dict[str, Any] = request.model_dump(exclude={"ip", "bind_user_email"})
    data_to_update["ip"] = str(request.ip)
    data_to_update["public_server_ip"] = str(request.public_server_ip)
    data_to_update["bind_user_id"] = bind_db_user.id if bind_db_user is not None else None

    if bind_db_user is not None:
        data_to_update["hashed_value"] = hashlib.sha256(
            f"{bind_db_user.email}{data_to_update['ip']}".encode(ENCODING)
        ).hexdigest()[::2]

    modem = crud.update_modem(db, db_modem, data_to_update)
    show_modem = schemas.ShowModem(
        **jsonable_encoder(modem, exclude={"bind_user"}),
        bind_user_email=str(bind_db_user.email) if bind_db_user is not None else None,
    )
    return show_modem


@router.delete(
    "/modems/{ip}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(JWTBearer())],
    description="Delete a modem by the given IP.",
    operation_id="delete-modem-by-ip",
    responses={204: {"description": "Successfully"}},
)
async def delete_modem(ip: IPvAnyAddress, db: DatabaseDependency) -> None:
    """
    Delete a modem with `ip`.
    """
    crud.delete_modem(db, str(ip))


@router.get(
    "/modems/change_ip_urls/{email}",
    response_model=list[schemas.ChangeIPUrl],
    dependencies=[Depends(JWTBearer())],
    status_code=status.HTTP_200_OK,
    description="Get urls for changing IP for a modem(s) for a user with the given email.",
    operation_id="get-change-ip-urls",
    responses={
        400: {"description": "User not found"},
        422: {"description": "Sorting problems"},
        200: {"description": "Successfully"},
    },
)
async def get_change_ip_urls(
    request: Request,
    db: DatabaseDependency,
    email: EmailStr,
    order_by: Annotated[str, Query(description="Sorting criteria: ip, public_server_ip, port")] = "ip",
) -> list[schemas.ChangeIPUrl]:
    """
    Get url(s) for changing IP (by rebooting a modem) for a modem(s) for a user with the given email.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = get_user_by_email(db, valid_email)
    if db_user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email does not exists.")

    def get_urls_list(request: Request) -> list[schemas.ChangeIPUrl]:
        """
        Returns all urls for changing IP for all user's modems.

        Raises:
            HTTPException: if unable to sort response data by field received in `order_by` query param.
        """
        host = request.base_url.hostname
        server_port = request.base_url.port
        schema = request.base_url.scheme

        # try to sort user modems by the given criteria
        # if any of user modems has nullable values an exception will be raised
        try:
            user_modems: list[models.Modem] = sorted(db_user.user_modems, key=lambda m: getattr(m, order_by))  # type: ignore
        except TypeError as e:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Unable to sort records because some entries contain null values. ",
            ) from e

        url_pattern_default_ports = "{schema}://{host}/modems/{token}/{hashed_value}"
        url_pattern_other_ports = "{schema}://{host}:{port}/modems/{token}/{hashed_value}"
        urls: list[schemas.ChangeIPUrl] = []

        for modem in user_modems:
            ip = IPv4Address(modem.ip)
            modem_port = int(modem.port)  # type: ignore
            public_server_ip = IPv4Address(modem.public_server_ip) if modem.public_server_ip is not None else None
            if server_port in {80, 443}:
                url = url_pattern_default_ports.format(
                    schema=schema, host=host, token=db_user.token, hashed_value=modem.hashed_value
                )
            else:
                url = url_pattern_other_ports.format(
                    schema=schema, host=host, port=server_port, token=db_user.token, hashed_value=modem.hashed_value
                )
            url = Url(url)
            data = schemas.ChangeIPUrl(ip=ip, port=modem_port, public_server_ip=public_server_ip, url=url)
            urls.append(data)

        return urls

    return get_urls_list(request)


@router.get(
    "/modems/{token}/{hashed_value}",
    include_in_schema=False,
    status_code=status.HTTP_200_OK,
    description=(
        "Reboot a modem which should be found by the given `token` and `hashed_value`. "
        "Token and hashed value generates automatically during user creating and modem creating respectively."
    ),
    response_class=JSONResponse,
    operation_id="reboot-modem",
    responses={
        200: {"description": "IP changed"},
        404: {"description": "Modem not Found"},
        406: {"description": "Problems on socket server or modem side"},
    },
)
async def change_ip(
    token: Annotated[str, Path(max_length=32, min_length=32, description="User token")],
    hashed_value: Annotated[str, Path(max_length=32, min_length=32, description="Modem hashed value")],
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
