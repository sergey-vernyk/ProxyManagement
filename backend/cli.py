import asyncio
import logging
import os
import pathlib
import signal
import time
from datetime import datetime

import click
from config import get_settings
from sockets.async_server import (CONN_COUNT_FILE_LOCATION, PID_FILE_LOCATION,
                                  AsyncSocketServer)

settings = get_settings()
ENCODING = settings.default_encoding
SERVER_LOGS_LOCATION = "logs/server_logs"

logger = logging.getLogger("socket_server")


@click.group()
def cli_server() -> None:
    """
    CLI entrypoint for socket server.
    """


@click.command()
@click.option(
    "--host",
    "-h",
    type=click.STRING,
    required=True,
    default="localhost",
    show_default=True,
    help="The host the server is running on.",
)
@click.option("--port", "-p", type=click.INT, required=True, help="The port the server is listening on.")
def run(host: str, port: int) -> None:
    """
    Run the socket server.

    Args:
        host (str): the host the server is running on.
        port (int): the port is server is running on.
    """
    server = AsyncSocketServer(host, port)
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Stop server listening on %s:%d by pressing Ctrl+C", host, port)
    except Exception as e:
        logger.error("Error %s occurred while starting server on %s:%d", str(e), host, port)
    finally:
        if pathlib.Path(CONN_COUNT_FILE_LOCATION).exists():
            os.remove(CONN_COUNT_FILE_LOCATION)
        if pathlib.Path(PID_FILE_LOCATION).exists():
            os.remove(PID_FILE_LOCATION)


@click.command()
def stop() -> None:
    """
    Gracefully stop the running socket server by sending SIGTERM signal.
    """
    server_pid_file = pathlib.Path(PID_FILE_LOCATION)

    if not server_pid_file.exists():
        logger.error("PID file not found.")
        return

    try:
        pid = int(server_pid_file.read_text(encoding=ENCODING).strip())

        if pid is None:
            logger.error("PID is None or invalid.")
            return

        try:
            os.kill(pid, signal.SIGTERM)
            logger.info("Sent SIGTERM to server with PID %s", pid)
        except ProcessLookupError:
            logger.error("No process found with PID %s", pid)
        except PermissionError:
            logger.error("Permission denied to send signal to PID %s", pid)
        except Exception as e:
            logger.error("Error sending SIGTERM to PID %s: %s", pid, str(e))
    except ValueError:
        logger.error("Invalid PID value in PID file.")
    except Exception as e:
        logger.error("Error reading PID file: %s", str(e))
    finally:
        os.remove(PID_FILE_LOCATION)
        os.remove(CONN_COUNT_FILE_LOCATION)


@click.command()
@click.option(
    "--lines-count",
    "-lc",
    type=click.INT,
    default=0,
    show_default=True,
    help="Show number of lines in the log. If 0 show all lines.",
)
@click.option(
    "--last",
    "-l",
    type=click.BOOL,
    default=True,
    show_default=True,
    help="Show last lines in the log file. If False show first lines.",
)
@click.option("--follow", "-f", type=click.BOOL, default=False, show_default=True, help="Follow the logs.")
def logs(lines_count: int = 0, last: bool = True, follow: bool = False) -> None:
    """
    Show the content of most resent log file, taking in account logs rotating mechanism.

    Args:
        lines_count (int, optional): number of lines in the log to show.
            If 0 show all lines, else show number of lines defined in the variable.
        last (bool, optional): if True, show last lines in the log file, otherwise show first lines.
        follow (bool, optional): follow the logs (like tail -f commands). Defaults to False.
    """
    logs_dir = pathlib.Path(SERVER_LOGS_LOCATION)

    try:
        # get the last log file even if the file format has *.log1, *.log2 (logs rotating is enabled)
        # e.g, 2024-09-03.log2
        last_log_name = sorted(
            os.listdir(logs_dir),
            key=lambda l: (datetime.strptime(l.split(".")[0], "%Y-%m-%d"), l.split(".")[1]),
        ).pop()

        last_log_file = logs_dir / last_log_name
    except (FileNotFoundError, ValueError, IndexError) as e:
        click.echo(click.style(f"Error finding or reading log files: {e}", fg="red", bold=True))
        return

    if last_log_file.exists():
        with open(last_log_file, encoding=ENCODING) as file:
            log_lines: list[str] | None = None
            if not follow:
                lines = file.readlines()
                # show all log lines
                if not lines_count:
                    log_lines = [click.style(line, fg="cyan", bold=True) for line in lines]
                # show number of lines defined in `lines_count` variable
                else:
                    if last:
                        log_lines = [click.style(line, fg="cyan", bold=True) for line in lines[-lines_count:]]
                    else:
                        log_lines = [click.style(line, fg="cyan", bold=True) for line in lines[:lines_count]]

                click.echo_via_pager("".join(log_lines), color=True)
            else:
                file.seek(0, 2)
                try:
                    while True:
                        line = file.readline()
                        if line:
                            click.echo(line, nl=False)
                        else:
                            time.sleep(1)
                except KeyboardInterrupt:
                    click.echo(click.style("Interrupt following logs by pushing Ctrl+C.", bold=True, fg="red"))
    else:
        click.echo(click.style("Log file not found.", fg="red", bold=True))


@click.command()
def connection_number() -> None:
    """
    Returns current number of connections to the sever.
    """
    conn_count_file = pathlib.Path(CONN_COUNT_FILE_LOCATION)
    if conn_count_file.exists():
        conn_number = int(conn_count_file.read_text(encoding=ENCODING))
        click.echo(click.style(f"Current number of connection to the server is {conn_number}.", bold=True, fg="cyan"))
    else:
        click.echo(
            click.style(
                "The server has not accepted any connection from client yet.",
                bold=True,
                fg="red",
            )
        )


cli_server.add_command(run)
cli_server.add_command(stop)
cli_server.add_command(logs)
cli_server.add_command(connection_number)
