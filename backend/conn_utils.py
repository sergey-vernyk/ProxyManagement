import selectors
import socket
from typing import TypeAlias

from sockets.multiconn_client import SocketClient

Socket: TypeAlias = socket.socket
Selector: TypeAlias = selectors.DefaultSelector


def parse_modem_data(data: list[bytes]) -> dict:
    """
    Parses a list of bytes data to extract modem connection details.

    Args:
        data (list[bytes]): A list containing three byte strings:
            - The first element should be the modem's URL or IP address.
            - The second element should be the username for authentication.
            - The third element should be the password for authentication.

    Returns:
        dict: A dictionary with the following keys and values:
            - 'url': The modem's URL, prefixed with "http://".
            - 'username': The username for authentication.
            - 'password': The password for authentication.

    Raises:
        IndexError: If the input list does not contain exactly three elements.
        UnicodeDecodeError: If any of the byte strings cannot be decoded using UTF-8.
    """
    data_str: list[str] = [d.decode("utf-8") for d in data]
    return {"url": f"http://{data_str[0]}", "username": data_str[1], "password": data_str[2]}


def build_default_route_ip(ip: str, last_octet: str = "1") -> str:
    """
    Build modem default route (192.168.10.1) from the given `ip`.
    E.g. 192.168.10.100 -> 192.168.10.1
    """
    ip_octets = ip.split(".")
    ip_octets.pop()
    ip_octets.append(last_octet)
    return ".".join(ip_octets)


def send_data_to_socket_server(
    data_to_send: str, socket_host: str, socket_port: int, sock: Socket, selector: Selector
) -> None | bytes:
    """
    Sends `data_to_send` to a socket server and returns the response.

    Creates a `SocketClient`, sends the data, and processes the response from the server.

    Args:
        data_to_send (str): Data to send to the server.
        socket_host (str): Server hostname or IP address.
        socket_port (int): Server port number.
        selector (Selector): Selector for I/O event monitoring.

    Returns:
        None | bytes: Received data from the server, or None if no data received.
    """
    with SocketClient(socket_host, socket_port, sock, selector) as client:
        client.compose_data_to_send(data_to_send)
        client.run_event_loop()

    return client.received_data
