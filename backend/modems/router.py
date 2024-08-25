"""
Module contains endpoints for modems:
- create_modem
- get_modem
- get_all_modems
- update_modem
- delete_modem
- get_change_ip_urls
- change_ip (websocket)
- get_change_ip_page
"""

import datetime
import hashlib
from ipaddress import IPv4Address
from typing import Annotated, Any

from auth.auth_bearer import JWTBearer
from config import get_settings
from conn_utils import send_data_to_socket_server
from dependencies import DatabaseDependency
from fastapi import (APIRouter, Depends, HTTPException, Path, Query, WebSocket,
                     WebSocketDisconnect, status)
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from logs.logging_conf import get_endpoint_logger
from pydantic import EmailStr, IPvAnyAddress
from pydantic_core import Url
from starlette.templating import _TemplateResponse
from users.crud import get_user_by_email
from users.models import User
from validators import validate_email_format

from . import crud, models, schemas

settings = get_settings()
templates = Jinja2Templates(directory="templates")
logger = get_endpoint_logger()
router = APIRouter()

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
async def create_modem(request: Request, body: schemas.CreateModem, db: DatabaseDependency) -> schemas.ShowModem:
    """
    Create modem or raise an exception if modem with provided IP is already exists.
    """
    db_modem = crud.get_modem_by_ip(db, str(body.ip))
    if db_modem is not None:
        logger.info(
            f"Modem with the given IP {body.ip} is already exists.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Modem with the given IP is already exists.")

    bind_db_user: User | None = None
    if body.bind_user_email is not None:
        bind_db_user = db.query(User).filter(User.email == body.bind_user_email).first()
        if bind_db_user is None:
            logger.info(
                f"User with the given email {body.bind_user_email} does not exist.",
                extra={"client_ip": request.client.host if request.client is not None else None},
            )
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exist.")

    modem_data: dict[str, Any] = body.model_dump(
        exclude={"bind_user_email", "ip", "external_server_ip", "internal_server_ip"}
    )
    modem_data["bind_user_id"] = bind_db_user.id if bind_db_user is not None else None
    modem_data["ip"] = str(body.ip)
    modem_data["external_server_ip"] = str(body.external_server_ip) if body.external_server_ip is not None else None
    modem_data["internal_server_ip"] = str(body.internal_server_ip) if body.internal_server_ip is not None else None

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
async def get_modem(request: Request, ip: IPvAnyAddress, db: DatabaseDependency) -> schemas.ShowModem:
    """
    Return a modem by its `ip`.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        logger.info(
            f"Modem with the given IP {ip} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
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
    modems: list[models.Modem] = crud.get_all_modems(db, skip, limit)
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
async def update_modem(
    request: Request, ip: IPvAnyAddress, body: schemas.UpdateModem, db: DatabaseDependency
) -> schemas.ShowModem:
    """
    Update modem by its IP address.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        logger.info(
            f"Modem with the given IP {ip} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exist.")

    bind_db_user: User | None = None
    if body.bind_user_email is not None:
        bind_db_user = db.query(User).filter(User.email == body.bind_user_email).first()
        if bind_db_user is None:
            logger.info(
                f"User with the given email {body.bind_user_email} does not exist.",
                extra={"client_ip": request.client.host if request.client is not None else None},
            )
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User with the given email does not exists.")

    data_to_update: dict[str, Any] = body.model_dump(exclude={"ip", "bind_user_email"})
    data_to_update["ip"] = str(body.ip)
    data_to_update["external_server_ip"] = str(body.external_server_ip) if body.external_server_ip is not None else None
    data_to_update["internal_server_ip"] = str(body.internal_server_ip) if body.internal_server_ip is not None else None
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
async def delete_modem(request: Request, ip: IPvAnyAddress, db: DatabaseDependency) -> None:
    """
    Delete a modem with `ip`.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        logger.info(
            f"Modem with the given IP {ip} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modem with the given IP does not exist.")

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
        logger.info(
            f"Email is invalid. Reason: {e}",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    db_user = get_user_by_email(db, valid_email)
    if db_user is None:
        logger.info(
            f"User with the given email {email} does not exist.",
            extra={"client_ip": request.client.host if request.client is not None else None},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with the given email does not exists.")

    def get_urls_list(request: Request) -> list[schemas.ChangeIPUrl]:
        """
        Returns all urls for changing IP for all user's modems.

        Raises:
            HTTPException: if unable to sort response data by field received in `order_by` query param.
        """
        host = request.base_url.hostname
        server_port = request.headers.get("X-Forwarded-Port", request.base_url.port)
        schema = request.base_url.scheme

        # try to sort user modems by the given criteria
        # if any of user modems has nullable values an exception will be raised

        try:
            user_modems: list[models.Modem] = sorted(db_user.user_modems, key=lambda m: getattr(m, order_by))
        except TypeError as e:
            logger.error(
                "Unable to sort records because some entries contains null values.",
                extra={"client_ip": request.client.host if request.client is not None else None},
            )
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Unable to sort records because some entries contains null values. ",
            ) from e

        url_pattern_default_ports = "{schema}://{host}/modems/{token}/{hashed_value}"
        url_pattern_other_ports = "{schema}://{host}:{port}/modems/{token}/{hashed_value}"
        urls: list[schemas.ChangeIPUrl] = []

        for modem in user_modems:
            ip = IPv4Address(modem.ip)
            modem_port = int(modem.port)  # type: ignore
            external_server_ip = IPv4Address(modem.external_server_ip) if modem.external_server_ip is not None else None
            internal_server_ip = IPv4Address(modem.internal_server_ip) if modem.internal_server_ip is not None else None
            if server_port in {80, 443}:
                url = url_pattern_default_ports.format(
                    schema=schema, host=host, token=db_user.token, hashed_value=modem.hashed_value
                )
            else:
                url = url_pattern_other_ports.format(
                    schema=schema, host=host, port=server_port, token=db_user.token, hashed_value=modem.hashed_value
                )
            url = Url(url)
            data = schemas.ChangeIPUrl(
                ip=ip,
                port=modem_port,
                external_server_ip=external_server_ip,
                internal_server_ip=internal_server_ip,
                url=url,
            )
            urls.append(data)

        return urls

    return get_urls_list(request)


@router.websocket("/ws/modems/", name="change_ip")
async def change_ip(websocket: WebSocket, db: DatabaseDependency) -> None:
    """
     WebSocket endpoint to change the IP address of a modem.

    Parameters:
    - websocket (WebSocket): The WebSocket connection instance.
    - db (DatabaseDependency): The database session used to query and update modem data.

    Flow:
    1. The WebSocket connection is accepted.
    2. The server waits for a message from the client containing the modem ID.
    3. The modem associated with the provided modem ID is queried from the database.
    4. If the modem is found:
       a. Prepare a reboot command using the modem's details.
       b. Send the command to the modem via the socket server.
       c. Await the socket server's response, which should include the old and new IP addresses.
       d. If successful, send the old and new IP addresses to the client via WebSocket.
       e. Update the modem's reboot timestamp in the database.
    5. If the modem is not found, or if the socket server indicates failure, send an error message to the client.

    Exceptions:
    - Handles WebSocketDisconnect gracefully by logging the disconnection and closing the WebSocket.
    """
    await websocket.accept()

    try:
        # Wait for a message from the client with modem id
        modem_id = await websocket.receive_text()
        modem: models.Modem | None = db.query(models.Modem).get(int(modem_id))

        if modem is not None:
            reboot_data = schemas.ModemActionsData(
                ip=IPv4Address(modem.ip),
                port=int(modem.port),  # type: ignore
                internal_server_ip=IPv4Address(modem.internal_server_ip),
                proxy_login=modem.bind_user.proxy_login,
                proxy_password_plain=modem.bind_user.proxy_password_plain,
                username=str(modem.username) if modem.username is not None else None,
                password=str(modem.password) if modem.password is not None else None,
                action=schemas.ModemAction.REBOOT,
            )

            reboot_data_str = reboot_data.convert_to_string_to_send()

            received_data = await send_data_to_socket_server(reboot_data_str, SOCKET_HOST, SOCKET_PORT)
            if received_data is not None:
                if b"Failed" in received_data:
                    await websocket.send_json({"error": received_data.decode(ENCODING)})
                    await websocket.close()
                    return

                old_ip, new_ip = received_data.decode(ENCODING).split()
                await websocket.send_json({"oldIp": old_ip, "newIp": new_ip})
                setattr(modem, "rebooted", datetime.datetime.now())
                db.commit()

    except WebSocketDisconnect as e:
        logger.info(
            f"Websocket client has been disconnected. Code: {e}",
            extra={"client_ip": websocket.client.host if websocket.client is not None else None},
        )
    else:
        await websocket.close()


@router.get(
    "/modems/{token}/{hashed_value}",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_change_ip_page(
    request: Request,
    token: Annotated[str, Path(max_length=32, min_length=32, description="User token")],
    hashed_value: Annotated[str, Path(max_length=32, min_length=32, description="Modem hashed value")],
    db: DatabaseDependency,
) -> _TemplateResponse:
    """
    HTTP GET endpoint to serve the modem IP change page.

    Parameters:
    - request (Request): The request object, containing information about the incoming request.
    - token (str): A 32-character string representing the user's token. Used to verify the user.
    - hashed_value (str): A 32-character string representing the hashed value of the modem. Used to identify the modem.
    - db (DatabaseDependency): The database session used to query modem data.

    Returns:
    - _TemplateResponse: Renders the "change_ip.html" template with WebSocket connection details.

    Flow:
    1. Query the database to find the modem associated with the provided `token` and `hashed_value`.
    2. Determine if the link is valid based on whether the modem is found.
    3. Extract the hostname, port, and schema (HTTP/HTTPS) from the request's base URL.
    4. Construct the appropriate WebSocket root URL (`ws_root_url`) based on the request schema:
       - For HTTPS, use `wss://`.
       - For HTTP, use `ws://`.
       - If the port is non-standard (not 80 or 443), include it in the URL.
    5. Render the "change_ip.html" template, passing the constructed `ws_root_url`, `token`, `hashed_value`,
       and `link_is_valid` to the template context.
    """
    modem = (
        db.query(models.Modem).join(User).filter(models.Modem.hashed_value == hashed_value, User.token == token).first()
    )
    link_is_valid = modem is not None

    host = request.base_url.hostname
    port = request.headers.get("X-Forwarded-Port", request.base_url.port)
    schema = request.base_url.scheme

    if schema == "https":
        ws_root_url = f"wss://{host}:{port}/ws/modems/" if port not in {80, 443} else f"wss://{host}/ws/modems/"
    elif schema == "http":
        ws_root_url = f"ws://{host}:{port}/ws/modems/" if port not in {80, 443} else f"ws://{host}/ws/modems/"

    print(ws_root_url)
    return templates.TemplateResponse(
        request,
        name="change_ip.html",
        context={
            "link_is_valid": link_is_valid,
            "modem_id": modem.id if modem is not None else None,
            "ws_root_url": ws_root_url,
            "token": token,
            "hashed_value": hashed_value,
        },
    )
