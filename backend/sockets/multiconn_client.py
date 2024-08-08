import logging
import selectors
import socket
import sys
import traceback
from dataclasses import dataclass, field
from typing import Optional, TypeAlias

from config import get_settings

settings = get_settings()

Socket: TypeAlias = socket.socket
Selector: TypeAlias = selectors.DefaultSelector
SelectorKey: TypeAlias = selectors.SelectorKey


START_CONNECTION = settings.socket_start_connection_cond.encode("utf-8")
STOP_CONNECTION = settings.socket_stop_connection_cond.encode("utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@dataclass
class ClientConnectionData:
    """
    Holds the data related to the client connection.

    Attributes:
        msg_total (int): Total message length to be sent.
        recv_total (int): Total length of received data.
        messages (list[bytes]): List of messages to be sent.
        outb (bytes): Buffer for outgoing data.
    """

    msg_total: int = 0
    recv_total: int = 0
    messages: list[bytes] = field(default_factory=list)
    outb: bytes = field(default_factory=bytes)


class SocketClient:
    """
    Manages a non-blocking TCP client socket using the selectors module.

    Handles connection to the server, data transmission, and event-driven
    communication.

    Attributes:
        _host (str): The hostname or IP address of the server.
        _port (int): The port number of the server.
        _socket (Socket): The client socket object.
        _selector (Selector): The selector object for monitoring I/O events.
        _connection_data (dict[Socket, ClientConnectionData]): Maps sockets to their connection data.
    """

    def __init__(self, host: str, port: int, socket: Socket, selector: Selector) -> None:
        self._host = host
        self._port = port
        self._socket = socket
        self._selector = selector
        self._connection_data: dict[Socket, ClientConnectionData] = {}

    def __enter__(self) -> "SocketClient":
        self.start_connection()
        return self

    def __exit__(
        self, exc_type: Optional[Exception], exc_val: Optional[Exception], exc_tb: Optional[traceback.TracebackException]
    ) -> None:
        self._selector.close()
        self._socket.close()

    def _clean_up(self, sock: Socket) -> None:
        """
        Cleans up the connection by unregistering the socket and closing it.

        Args:
            sock (Socket): The socket to clean up.
        """
        self._selector.unregister(sock)
        sock.close()
        del self._connection_data[sock]

    def start_connection(self) -> None:
        """
        Initializes the client socket and starts connecting to the server.
        """
        server_addr = (self._host, self._port)
        logging.info("Establishing connection to %s:%d", self._host, self._port)
        self._socket.setblocking(False)

        try:
            result: int = self._socket.connect_ex(server_addr)
            if not result:
                logging.error("Connection failed while establishing connection. Error code: %d", result)
                self._socket.close()
                sys.exit(1)
        except socket.error as e:
            logging.error("Socket error during connection: %s", e)
            self._socket.close()
            sys.exit(1)

        events: int = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = ClientConnectionData(
            msg_total=0,
            messages=[],
        )
        self._selector.register(self._socket, events, data=data)

    def compose_data_to_send(self, sending_data: str) -> None:
        """
        Prepares data to be sent and updates connection data.

        Args:
            sending_data (str): The data to be sent to the server, separated by commas.
        """
        messages: list[bytes] = [d.encode("utf-8") + b"\n" for d in sending_data.split(",")]
        messages.insert(0, START_CONNECTION)
        messages.append(STOP_CONNECTION)
        conn_data = ClientConnectionData(
            msg_total=sum(len(msg) for msg in messages),
            messages=messages,
        )
        events: int = selectors.EVENT_READ | selectors.EVENT_WRITE
        self._connection_data[self._socket] = conn_data
        self._selector.modify(self._socket, events, conn_data)

    def _handle_read_event(self, sock: Socket, data: ClientConnectionData) -> None:
        """
        Handles incoming data from the server and checks for completion.

        Args:
            sock (Socket): The socket from which data is being read.
            data (ClientConnectionData): The connection data associated with the socket.
        """
        try:
            recv_data: bytes = sock.recv(1024)
            if recv_data:
                logging.info("Received %r from connection %s:%d", recv_data, self._host, self._port)
                data.recv_total += len(recv_data)
            if b"OK" in recv_data or data.recv_total == data.msg_total:
                logging.info("Closing connection to %s:%d", self._host, self._port)
                data.recv_total = 0
                data.msg_total = 0
                self._clean_up(sock)
        except Exception as e:
            logging.error("Exception during read: %s", e)
            self._clean_up(sock)

    def _handle_write_event(self, sock: Socket, data: ClientConnectionData) -> None:
        """
        Handles sending data to the server from the outgoing buffer.

        Args:
            sock (Socket): The socket used to send data.
            data (ClientConnectionData): The connection data associated with the socket.
        """
        try:
            if data.messages:
                data.outb = data.messages.pop(0)
            if data.outb:
                logging.info("Sending %s to connection %s:%d", data.outb.strip(b"\n"), self._host, self._port)
                sent: int = sock.send(data.outb)
                data.outb = data.outb[sent:]
                data.msg_total = sum(len(msg) for msg in data.messages)
        except Exception as e:
            logging.error("Exception during write: %s", e)
            data.msg_total = 0
            data.recv_total = 0
            data.outb = b""
            self._clean_up(sock)

    def _handle_connection(self, key: SelectorKey, mask: int) -> None:
        """
        Processes read and write events for a client connection based on the mask.

        Args:
            key (SelectorKey): The key for the selector event.
            mask (int): The event mask indicating read or write events.
        """
        sock: Socket = key.fileobj  # type: ignore
        data: ClientConnectionData = key.data
        if mask & selectors.EVENT_READ:
            self._handle_read_event(sock, data)
        if mask & selectors.EVENT_WRITE:
            self._handle_write_event(sock, data)

    def run_event_loop(self) -> None:
        """
        Main event loop for handling client socket events until all connections are closed.
        """
        try:
            while self._connection_data:
                events: list[tuple[SelectorKey, int]] = self._selector.select(timeout=1)
                for key, mask in events:
                    if key.data is None:
                        logging.warning("Unexpected event for listening socket.")
                        continue

                    self._handle_connection(key, mask)
        except KeyboardInterrupt:
            logging.info("Stopping connection with the server %s:%d", self._host, self._port)
        except Exception as e:
            logging.error("Exception in event loop: %s", e)
        finally:
            self._selector.close()


if __name__ == "__main__":
    sel = selectors.DefaultSelector()
    sock_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with SocketClient(host=settings.socket_host, port=settings.socket_port, socket=sock_obj, selector=sel) as client:
        client.compose_data_to_send("hello world!,How are you?,London is the capital of Great Britain")
        client.run_event_loop()
