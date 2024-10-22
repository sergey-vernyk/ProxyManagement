import asyncio
import os
import pathlib
from dataclasses import dataclass, field
from ipaddress import IPv4Address

from config import get_settings
from conn_utils import build_default_route_ip, parse_modem_data_to_reboot
from logs.logging_conf import get_socket_server_logger
from modem_api import reboot_modem

from . import (CONN_COUNT_FILE, ENCODING, PID_FILE, START_CONNECTION,
               STOP_CONNECTION)

settings = get_settings()

logger = get_socket_server_logger()


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


async def fetch_ip(
    proxy_login: str, proxy_password: str, proxy_port: int, internal_server_ip: IPv4Address, fetch_attempts: int = 5
) -> str | None:
    """
    Fetches the current external IP using the modem's proxy settings.
    """
    for _ in range(fetch_attempts):
        try:
            process = await asyncio.create_subprocess_exec(
                "curl",
                "-s",
                "--fail",
                "--max-time",
                f"{settings.max_time_curl}",
                "-U",
                f"{proxy_login}:{proxy_password}",
                "-x",
                f"http://{internal_server_ip}:{proxy_port}",
                "ifconfig.me",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return stdout.decode(ENCODING).strip()
            if process.returncode == 22:
                await asyncio.sleep(2)
                continue
            logger.error("Failed to fetch IP: %s", stderr.decode(ENCODING))
            break
        except Exception as e:
            logger.error("Exception during IP fetch: %s.", e)
            break


async def handle_modem_rebooting(message: list[bytes], data: ServerConnectionData, reboot_attempts: int = 3) -> None:
    """
    Asynchronously attempts to reboot a modem up to a specified number of times and handles the connection response.

    Args:
        message (list[bytes]): Incoming data containing modem information.
        data (ServerConnectionData): Server connection data for sending responses.
        reboot_attempts (int): Maximum number of reboot attempts. Defaults to 3.
    """
    modem_reboot_data = parse_modem_data_to_reboot(message)
    modem_default_route = build_default_route_ip(modem_reboot_data.ip)

    ip_before = await fetch_ip(
        modem_reboot_data.proxy_login,
        modem_reboot_data.proxy_password_plain,
        modem_reboot_data.port,
        modem_reboot_data.internal_server_ip,
        settings.fetch_ip_attempts,
    )
    if ip_before is None:
        logger.error("Fetch IP failed.")
        data.outb += b"Failed to fetch IP. Probably, there are some problems with internet connection."
        return

    logger.info("IP before reboot: %s.", ip_before)

    ip_after: str | None = None
    rebooted = False

    for i in range(reboot_attempts):
        if rebooted:
            break

        rebooted = reboot_modem(
            url=f"http://{modem_default_route}",
            username=modem_reboot_data.username,
            password=modem_reboot_data.password,
        )
        if rebooted is True:
            await asyncio.sleep(settings.delay_after_reboot)  # Wait for the modem to reboot
            while True:
                try:
                    # Check if the modem has come back online by fetching the IP again
                    ip_after = await fetch_ip(
                        modem_reboot_data.proxy_login,
                        modem_reboot_data.proxy_password_plain,
                        modem_reboot_data.port,
                        modem_reboot_data.internal_server_ip,
                        settings.fetch_ip_attempts,
                    )
                    if ip_after is not None and ip_after != ip_before:
                        data.outb += f"{ip_before}\n".encode(ENCODING)
                        data.outb += f"{ip_after}\n".encode(ENCODING)
                        data.outb += b"OK"
                        logger.info("Reboot successful: IP before %s, IP after %s.", ip_before, ip_after)
                        break
                    #! break - test it thoroughly
                except Exception as e:
                    logger.error("Error checking modem status: %s.", e)
                    break
        else:
            logger.warning("Attempt %d failed: %s", i + 1, "Not rebooted")
            await asyncio.sleep(2)
            continue

    if rebooted is True and ip_after is None:
        logger.error("Failed to fetch IP after modem rebooting.")
        data.outb += b"Failed to fetch IP after modem rebooting."
        return

    if rebooted is False:
        logger.error("Modem reboot failed after %d attempts", reboot_attempts)
        data.outb += b"Failed to reboot modem."


class AsyncSocketServer:
    """
    A class to manage an asynchronous TCP server using asyncio.

    The AsyncSocketServer class handles multiple client connections concurrently, manages
    the reception and transmission of data, and processes specific client requests such
    as reboot commands.

    Attributes:
        _host (str): The hostname or IP address on which the server listens.
        _port (int): The port number on which the server listens.
        _connection_data (dict): A dictionary that maps StreamWriter objects to ServerConnectionData instances.
        _socket (Optional[asyncio.AbstractServer]): The server socket object.
        _conn_id_counter (int): A counter to generate unique connection IDs for clients.

    Methods:
        start_server(): Starts the server and listens for incoming connections.
        accept_connection(reader, writer): Accepts and handles data from a new client connection.
        _get_message_indexes(input_data): Finds the start and stop indexes for message boundaries within the input data.
        _get_next_conn_id(): Generates and returns the next unique connection ID.
        _clean_up(writer): Cleans up the server state after a connection is closed.
    """

    _conn_id_counter = 0

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._connection_data: dict[asyncio.StreamWriter, ServerConnectionData] = {}
        self._socket: asyncio.AbstractServer | None = None

    @staticmethod
    def _save_conn_id_to_file(conn_id: str) -> None:
        """
        Save connection ID to the file.

        Args:
            conn_id (str): connection ID which will be saved.
        """
        conn_count_file = pathlib.Path(CONN_COUNT_FILE)
        conn_count_file.write_text(conn_id, encoding=ENCODING)

    @classmethod
    def _get_conn_id(cls, incr: bool) -> int:
        """
        Get number of accepted connection.

        Args:
            incr (bool):
                - increment current number of connection if the server accepted new connection.
                - decrement current number of connections if a client closed the connection.

        Returns:
            int: current number of connections.
        """
        if incr:
            cls._conn_id_counter += 1
        else:
            cls._conn_id_counter -= 1

        cls._save_conn_id_to_file(str(cls._conn_id_counter))
        return cls._conn_id_counter

    def _clean_up(self, writer: asyncio.StreamWriter) -> None:
        """
        Cleans up the server state after a connection is closed.

        This method removes the connection data associated with the given writer
        from the server's internal tracking and logs the closure.

        Args:
            writer (asyncio.StreamWriter): The stream writer for the client connection.
        """
        writer_connection = self._connection_data[writer].addr
        # +1 because the method already subtract 1 from connection number
        current_conn_id = self._get_conn_id(incr=False) + 1
        logger.info("Closing connection %d on %s:%d", current_conn_id, writer_connection[0], writer_connection[1])
        del self._connection_data[writer]

    async def start_server(self) -> None:
        """
        Starts the server and begins listening for incoming connections.

        This method opens a server socket and waits for incoming client connections.
        Once a connection is accepted, it hands off the connection to `accept_connection`.
        """
        self._socket = await asyncio.start_server(self.accept_connection, self._host, self._port)
        addr = self._socket.sockets[0].getsockname()
        logger.info("Listening on %s:%d", addr[0], addr[1])
        self._save_pid()

        async with self._socket:
            await self._socket.serve_forever()

    @staticmethod
    def _save_pid() -> None:
        """
        Save PID of a current process to the file.
        This PID will be used for graceful terminated a server by CLI.
        """
        pid: int = os.getpid()
        pid_file = pathlib.Path(PID_FILE)
        pid_file.write_text(str(pid), encoding=ENCODING)

    @staticmethod
    def _get_message_indexes(input_data: bytes) -> tuple[int, int]:
        """
        Finds the start and stop indexes for message boundaries within the input data.

        Args:
            input_data (bytes): The raw input data received from the client.

        Returns:
            tuple[int, int]: A tuple containing the start and stop indexes of the message.
        """
        start_idx, stop_idx = -1, -1
        if START_CONNECTION in input_data:
            start_idx: int = input_data.index(START_CONNECTION) + len(START_CONNECTION)

        if STOP_CONNECTION in input_data:
            stop_idx: int = input_data.index(STOP_CONNECTION)

        return start_idx, stop_idx

    async def accept_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        Accepts and handles data from a new client connection.

        This method processes incoming data from the client, checks for specific
        commands such as "reboot", and sends responses back to the client.

        Args:
            reader (asyncio.StreamReader): The stream reader for the client connection.
            writer (asyncio.StreamWriter): The stream writer for the client connection.
        """
        addr = writer.get_extra_info("peername")
        conn_id = self._get_conn_id(incr=True)
        logger.info("Accepted connection %d from %s:%d", conn_id, addr[0], addr[1])

        data = ServerConnectionData(addr=addr, connid=conn_id)
        self._connection_data[writer] = data

        try:
            while True:
                data_in = await reader.read(1024)
                if not data_in:
                    break
                data.inb += data_in
                if START_CONNECTION in data.inb and STOP_CONNECTION in data.inb:
                    start_idx, stop_idx = self._get_message_indexes(data.inb)
                    message = data.inb[start_idx:stop_idx].split(b"\n")[:-1]
                    logger.info("Received data %s from %s:%d", message, addr[0], addr[1])
                    if b"reboot" in message:
                        await handle_modem_rebooting(message, data, settings.reboot_attempts)
                        if data.outb:
                            writer.write(data.outb)
                            await writer.drain()
        except asyncio.CancelledError:
            logger.info("Connection with %s:%d was cancelled", addr[0], addr[1])
        finally:
            writer.close()
            await writer.wait_closed()
            self._clean_up(writer)


if __name__ == "__main__":
    SOCKET_HOST = "localhost"
    SOCKET_PORT = 65432
    server = AsyncSocketServer(SOCKET_HOST, SOCKET_PORT)

    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Stop listening on %s:%d", SOCKET_HOST, SOCKET_PORT)
