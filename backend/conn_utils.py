import asyncio
import itertools
import selectors
import signal
import socket
from dataclasses import fields
from ipaddress import IPv4Address
from typing import TypeAlias

from modems.schemas import ModemAction, ModemActionsData
from sockets.async_client import AsyncSocketClient, handle_shutdown

Socket: TypeAlias = socket.socket
Selector: TypeAlias = selectors.DefaultSelector


def parse_modem_data_to_reboot(data: list[bytes]) -> ModemActionsData:
    """
    Parses a list of byte strings to create a ModemActionsData object.

    Args:
        data (list[bytes]): A list containing modem details in the following order:
            1. IP address
            2. Port number
            3. Internal server IP address
            4. Proxy login
            5. Proxy password
            6. Username
            7. Password
            8. Action to perform

    Returns:
        ModemActionsData: An object with the parsed modem details.
    """
    data_keys: list[str] = [field.name for field in fields(ModemActionsData)]
    data_values: list[str] = [d.decode("utf-8") for d in data]
    data_dict = dict(itertools.zip_longest(data_keys, data_values, fillvalue=None))

    modem_reboot_data = ModemActionsData(
        ip=IPv4Address(data_dict["ip"]),
        port=int(data_dict["port"]),  # type: ignore
        internal_server_ip=IPv4Address(data_dict["internal_server_ip"]),
        proxy_login=data_dict["proxy_login"],  # type: ignore
        proxy_password_plain=data_dict["proxy_password_plain"],  # type: ignore
        username=data_dict["username"],
        password=data_dict["password"],
        action=ModemAction(data_dict["action"]),
    )
    return modem_reboot_data


def build_default_route_ip(ip: IPv4Address, last_octet: str = "1") -> str:
    """
    Build modem default route (192.168.10.1) from the given `ip`.
    E.g. 192.168.10.100 -> 192.168.10.1
    """
    str_ip = ip.exploded
    ip_octets = str_ip.split(".")
    ip_octets.pop()
    ip_octets.append(last_octet)
    return ".".join(ip_octets)


async def send_data_to_socket_server(data_to_send: str, socket_host: str, socket_port: int) -> None | bytes:
    """
    Asynchronously sends `data_to_send` to a socket server and returns the response.

    Creates an `AsyncSocketClient`, establishes a connection, sends the data, and processes the response
    from the server.

    Args:
        data_to_send (str): Data to send to the server. This data will be sent as a string.
        socket_host (str): Server hostname or IP address to which the data will be sent.
        socket_port (int): Server port number for the connection.

    Returns:
        None | bytes: Received data from the server. If no data is received, returns None.
    """
    client = AsyncSocketClient(socket_host, socket_port)

    loop = asyncio.get_event_loop()
    # Register the signal handler for shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown, client)

    try:
        await client.run(data_to_send)
    except ConnectionRefusedError:
        return b"Failed connection with the server."

    return client.received_data
