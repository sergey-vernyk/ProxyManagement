import datetime
from ipaddress import IPv4Address

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..common.utils import get_caller_info
from ..config import get_settings
from ..conn_utils import send_data_to_socket_server
from ..dependencies import DatabaseDependency
from ..logs.logging_conf import build_ip_address_for_log, get_endpoint_logger
from . import models, schemas

settings = get_settings()
router = APIRouter()
logger = get_endpoint_logger()
ENCODING: str = settings.default_encoding


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
                port=modem.port,
                internal_server_ip=IPv4Address(modem.internal_server_ip),
                proxy_login=modem.bind_user.proxy_login,
                proxy_password_plain=modem.bind_user.proxy_password_plain,
                username=modem.username if modem.username is not None else None,
                password=modem.password if modem.password is not None else None,
                action=schemas.ModemAction.REBOOT,
            )

            reboot_data_str = reboot_data.convert_to_string_to_send()

            received_data = await send_data_to_socket_server(
                reboot_data_str, modem.internal_server_ip, modem.external_server_port
            )
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
            extra={
                "client_ip": build_ip_address_for_log(websocket.client.host) if websocket.client is not None else None,
                **get_caller_info(),
            },
        )
    else:
        await websocket.close()
