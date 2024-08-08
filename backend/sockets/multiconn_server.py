import logging
import selectors
import socket
import traceback
from dataclasses import dataclass, field
from time import sleep
from typing import Optional, TypeAlias

from config import get_settings
from conn_utils import parse_modem_data
from modem_api import reboot_modem

settings = get_settings()


Socket: TypeAlias = socket.socket
Selector: TypeAlias = selectors.DefaultSelector
SelectorKey: TypeAlias = selectors.SelectorKey

ENCODING: str = settings.default_encoding
START_CONNECTION: bytes = settings.socket_start_connection_cond.encode(ENCODING)
STOP_CONNECTION: bytes = settings.socket_stop_connection_cond.encode(ENCODING)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@dataclass
class ServerConnectionData:
    """
    Stores data associated with a client connection.

    This class holds information about a specific client connection,
    including the client's address, a unique connection ID, and buffers
    for incoming and outgoing data.

    Attributes:
        addr (tuple[str, int]): The address of the client connection, consisting
            of a hostname (or IP address) and a port number.
        connid (int): A unique identifier for the connection. Defaults to 0.
        inb (bytes): A buffer for storing incoming data from the client. Defaults to an empty bytes object.
        outb (bytes): A buffer for storing outgoing data to be sent to the client. Defaults to an empty bytes object.
    """

    addr: tuple[str, int]
    connid: int = 0
    inb: bytes = field(default_factory=bytes)
    outb: bytes = field(default_factory=bytes)


class SocketServer:
    """
    A non-blocking TCP server using the `selectors` module for asynchronous I/O operations.

    This class creates a TCP server capable of handling multiple clients simultaneously
    using non-blocking sockets. It manages accepting new client connections, reading from
    clients, and sending data to clients in an asynchronous manner.

    Attributes:
        _host (str): The hostname or IP address on which the server will listen.
        _port (int): The port number on which the server will listen.
        _socket (Socket): The server socket object used for listening and accepting new connections.
        _selector (Selector): The selector object used to monitor I/O events on sockets.
        _connection_data (dict[Socket, ServerConnectionData]): A dictionary mapping client sockets to their
            associated `ServerConnectionData`.
    """

    __connection_id = 0

    def __init__(self, host: str, port: int, socket: Socket, selector: Selector) -> None:
        """
        Initializes the server instance.

        Args:
            host (str): The hostname or IP address to bind the server socket to.
            port (int): The port number to bind the server socket to.
            socket (Socket): The server socket object used for accepting connections.
            selector (Selector): The selector object used for monitoring I/O events.
        """
        self._host = host
        self._port = port
        self._socket = socket
        self._selector = selector
        self._connection_data: dict[Socket, ServerConnectionData] = {}
        self._initialized = False

    def __enter__(self) -> "SocketServer":
        self.init_server()
        self._initialized = True
        return self

    def __exit__(
        self, exc_type: Optional[Exception], exc_val: Optional[Exception], exc_tb: Optional[traceback.TracebackException]
    ) -> None:
        self._selector.close()
        self._socket.close()

    @classmethod
    def _get_next_conn_id(cls) -> int:
        """
        Generates the next connection ID.

        Returns:
            int: The next available connection ID.
        """
        cls.__connection_id += 1
        return cls.__connection_id

    @classmethod
    def _set_prev_conn_id(cls) -> None:
        """
        Decrements the connection ID counter by one.
        """
        cls.__connection_id -= 1

    def _clean_up(self, sock: Socket) -> None:
        """
        Cleans up the connection when a client disconnects or an error occurs.

        Args:
           sock (Socket): The socket associated with the connection to clean up.
        """
        self._selector.unregister(sock)
        sock.close()
        self._set_prev_conn_id()
        del self._connection_data[sock]

    def init_server(self) -> None:
        """
        Initializes the server by binding it to the specified host and port,
        setting it to non-blocking mode, and registering it with the selector
        for monitoring incoming connections.
        """
        self._socket.bind((self._host, self._port))
        self._socket.listen()
        logging.info("Listening on %s:%d", self._host, self._port)
        self._socket.setblocking(False)
        self._selector.register(fileobj=self._socket, events=selectors.EVENT_READ, data=None)

    def _accept_connection(self, sock: Socket) -> None:
        """
        Accepts a new client connection, sets it to non-blocking mode, and
        registers it with the selector.

        Args:
            sock (Socket): The listening socket used to accept new connections.
        """
        try:
            conn, addr = sock.accept()
            conn.setblocking(False)
            connid: int = self._get_next_conn_id()
            logging.info("Accepted connection %d from client: %s:%d", connid, addr[0], addr[1])
            data = ServerConnectionData(addr=addr, connid=connid)
            self._connection_data[conn] = data
            events: int = selectors.EVENT_READ | selectors.EVENT_WRITE
            self._selector.register(conn, events, data)
        except Exception as e:
            logging.error("Exception during accept: %s", e)

    def _get_message_indexes(self, input_data: bytes) -> tuple[int, int]:
        """
        Finds the start and stop indexes for message boundaries within the input data.

        Args:
            input_data (bytes): The raw input data received from the client.

        Returns:
            tuple[int, int]: A tuple containing the start and stop indexes of the message.
        """
        if START_CONNECTION in input_data:
            start_idx: int = input_data.index(START_CONNECTION) + len(START_CONNECTION)

        if STOP_CONNECTION in input_data:
            stop_idx: int = input_data.index(STOP_CONNECTION)

        return start_idx, stop_idx

    def _handle_read_event(self, sock: Socket, data: ServerConnectionData) -> None:
        """
        Handles incoming data from a client socket. Processes received data
        and checks for the start and stop indicators. Closes the connection if
        no data is received.

        Args:
            sock (Socket): The socket from which data is being read.
            data (ServerConnectionData): The connection data associated with the socket.
        """
        try:
            recv_data: bytes = sock.recv(1024)

            if not recv_data:
                self._clean_up(sock)
                logging.info("Closing connection from %s:%d", data.addr[0], data.addr[1])
                return

            data.inb += recv_data
            if START_CONNECTION in data.inb and STOP_CONNECTION in data.inb:
                start_idx, stop_idx = self._get_message_indexes(data.inb)
                message: list[bytes] = data.inb[start_idx:stop_idx].split(b"\n")[:-1]
                logging.info("Received data %s from %s:%d", message, data.addr[0], data.addr[1])
                modem_conn_data = parse_modem_data(message)

                reboot_attempts = 0
                while reboot_attempts < 3:
                    result: str = reboot_modem(**modem_conn_data)
                    if result == "Not Rebooted":
                        reboot_attempts += 1
                        sleep(2)
                        data.outb = result.encode(ENCODING)
                        continue

                    if result == "Rebooted":
                        data.outb += result.encode(ENCODING) + b"\n"
                        data.outb += b"OK"
                        break

                    if "Error:" in result:
                        data.outb = result.encode(ENCODING)
                        break
                else:
                    data.outb = b"Failed to reboot modem"
        except Exception as e:
            logging.error("Exception during read: %s", e)
            self._clean_up(sock)

    def _handle_write_event(self, sock: Socket, data: ServerConnectionData) -> None:
        """
        Handles sending data to the client socket. Sends data from the `outb`
        buffer to the client and updates the buffer to reflect the amount of
        data sent.

        Args:
            sock (Socket): The socket to which data is being sent.
            data (ServerConnectionData): The connection data associated with the socket.
        """
        try:
            if data.outb:
                sent: int = sock.send(data.outb)
                data.outb = data.outb[sent:]
        except Exception as e:
            logging.error("Exception during write: %s", e)
            self._clean_up(sock)

    def _handle_connection(self, key: SelectorKey, mask: int) -> None:
        """
        Processes I/O events for a client connection based on the provided mask.
        Calls the appropriate read or write event handler.

        Args:
            key (SelectorKey): The key object from the selector.
            mask (int): The event mask indicating which events are triggered.
        """
        sock: Socket = key.fileobj  # type: ignore
        data: ServerConnectionData | None = self._connection_data.get(sock)

        if data is None:
            logging.warning("No connection data found for the socket. Ignoring.")
            return

        if mask & selectors.EVENT_READ:
            self._handle_read_event(sock, data)
        if mask & selectors.EVENT_WRITE:
            self._handle_write_event(sock, data)

    def run_event_loop(self) -> None:
        """
        Starts the main event loop for accepting and serving client connections.
        Continuously monitors for I/O events and dispatches them to the appropriate handlers.

        Raises:
            RuntimeError: If the server is not initialized before starting the event loop.
        """
        if not self._initialized:
            raise RuntimeError("Server is not initialized. Call `init_server` before starting the event loop.")

        try:
            while True:
                events: list[tuple[SelectorKey, int]] = self._selector.select(timeout=1)
                for key, mask in events:
                    # means it’s from the listening socket and you need to accept the connection
                    if key.data is None:
                        self._accept_connection(sock=key.fileobj)  # type: ignore
                    else:  # means that it's a client socket that's already been accepted
                        self._handle_connection(key=key, mask=mask)
        except KeyboardInterrupt:
            logging.info("Stop listening on %s:%d", self._host, self._port)
        except Exception as e:
            logging.error("Exception in event loop: %s", e)
        finally:
            logging.info("Cleaning up resources.")
            self._selector.close()
            self._socket.close()


if __name__ == "__main__":
    sel = selectors.DefaultSelector()
    sock_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with SocketServer(host=settings.socket_host, port=settings.socket_port, socket=sock_obj, selector=sel) as server:
        server.run_event_loop()
