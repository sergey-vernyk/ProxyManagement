import asyncio
import signal
from dataclasses import dataclass, field
from typing import Any

from config import get_settings
from logs.logging_conf import get_client_logger

settings = get_settings()


ENCODING: str = settings.default_encoding
START_CONNECTION: bytes = settings.socket_start_connection_cond.encode(ENCODING)
STOP_CONNECTION: bytes = settings.socket_stop_connection_cond.encode(ENCODING)

logger = get_client_logger()


@dataclass
class ClientConnectionData:
    """
    Holds the data related to the client connection.

    Attributes:
        msg_total (int): Total length of messages to be sent to the server.
        recv_total (int): Total length of data received from the server.
        messages (list[bytes]): List of messages to be sent to the server.
        outb (bytes): Buffer for outgoing data.
        inb (bytes): Buffer for incoming data.
    """

    msg_total: int = 0
    recv_total: int = 0
    messages: list[bytes] = field(default_factory=list)
    outb: bytes = field(default_factory=bytes)
    inb: bytes = field(default_factory=bytes)


class AsyncSocketClient:
    """
    Manages an asynchronous TCP client socket using asyncio.

    Handles connection to the server, data transmission, and event-driven communication.

    Attributes:
        _host (str): The hostname or IP address of the server.
        _port (int): The port number of the server.
        _reader (asyncio.StreamReader): The reader stream for the client connection.
        _writer (asyncio.StreamWriter): The writer stream for the client connection.
        _connection_data (ClientConnectionData): Connection data for managing sent and received data.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connection_data: ClientConnectionData | None = None
        self._closing: bool = False
        self._received_data: bytes | None = None

    @property
    def received_data(self) -> bytes | None:
        """
        Gets the data received from the server after the connection has been closed.

        Returns:
            Optional[bytes]: The data received from the server, or None if no data was received.
        """
        return self._received_data

    async def start_connection(self) -> None:
        """
        Initializes the client socket and starts connecting to the server.
        """
        logger.info("Establishing connection to %s:%d", self._host, self._port)
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)

        # Initialize connection data
        self._connection_data = ClientConnectionData()

    async def compose_data_to_send(self, sending_data: str) -> None:
        """
        Prepares data to be sent and updates connection data.

        Args:
            sending_data (str): The data to be sent to the server, separated by commas.
        """
        messages: list[bytes] = [d.encode(ENCODING) + b"\n" for d in sending_data.split(",")]
        messages.insert(0, START_CONNECTION)
        messages.append(STOP_CONNECTION)

        if self._connection_data is not None:
            self._connection_data.messages = messages
            self._connection_data.msg_total = sum(len(msg) for msg in messages)

        await self._send_messages()

    async def _send_messages(self) -> None:
        """
        Handles sending data to the server from the outgoing buffer.
        """
        if self._connection_data is None or self._writer is None:
            return

        while self._connection_data.messages:
            message: bytes = self._connection_data.messages.pop(0)
            self._writer.write(message)
            await self._writer.drain()
            logger.info("Sent %s to server %s:%d", message.strip(b"\n"), self._host, self._port)

        await self._receive_response()

    async def _receive_response(self) -> None:
        """
        Handles receiving data from the server.
        """
        if self._connection_data is None or self._reader is None:
            return

        while True:
            recv_data: bytes = await self._reader.read(1024)
            if not recv_data:
                break

            logger.info("Received %r from server %s:%d", recv_data, self._host, self._port)
            self._connection_data.recv_total += len(recv_data)

            if b"OK" in recv_data:
                in_data = recv_data.split(b"\n")[:-1]
                self._connection_data.inb += in_data[0] + b" "
                self._connection_data.inb += in_data[1]
                logger.info("Server confirmed reception. Closing connection.")
                await self._clean_up()
                break

            if b"Error:" in recv_data:
                logger.error("Server error: %s", recv_data.decode(ENCODING))
                await self._clean_up()
                break

    async def _clean_up(self) -> None:
        """
        Cleans up the connection by closing the writer and setting data to None.
        """
        if self._connection_data is not None:
            in_data: bytes = self._connection_data.inb
            if in_data:
                self._received_data = in_data

        if self._writer is not None and not self._closing:
            self._closing = True
            self._writer.close()
            await self._writer.wait_closed()
            logger.info("Connection to server %s:%d closed", self._host, self._port)

        self._reader = None
        self._writer = None
        self._connection_data = None

    async def stop(self) -> None:
        """
        Method to close the connection programmatically.
        """
        await self._clean_up()

    async def run(self, sending_data: str) -> None:
        """
        Starts the client, sends data, and handles communication.

        Args:
            sending_data (str): The data to be sent to the server.
        """
        try:
            await self.start_connection()
            await self.compose_data_to_send(sending_data)
        except asyncio.CancelledError:
            logger.info("Client operation was cancelled.")
            await self._clean_up()


def handle_shutdown(client: AsyncSocketClient) -> None:
    """
    Handles shutdown signals like Ctrl+C to close the client connection gracefully.
    """
    logger.info("Shutdown signal received. Closing client connection...")
    asyncio.create_task(client.stop())


if __name__ == "__main__":
    host = settings.socket_host
    port = settings.socket_port
    client = AsyncSocketClient(host, port)

    # Create the event loop explicitly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Register the signal handler for shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown, client)

    try:
        loop.run_until_complete(client.run("hello world!"))
    except KeyboardInterrupt:
        logger.info("Client interrupted by user")
    finally:
        pending: set[asyncio.Task[Any]] = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending))
        loop.close()
