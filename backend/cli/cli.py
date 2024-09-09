import asyncio
import os
import pathlib
import signal
import time
from datetime import datetime

import click
import uvicorn
from logs.logging_conf import get_socket_server_logger

logger = get_socket_server_logger()


@click.group()
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    required=True,
    help="Location of the environment configuration file.",
)
def cli_server(env_file: pathlib.Path) -> None:
    """
    CLI entrypoint for socket server.

    Loads the environment variables from the provided file.

    Args:
        env_file (pathlib.Path): Path to the environment configuration file.
    """
    os.environ["ENV_FILE_PATH"] = str(env_file)


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
@click.option("--port", "-p", type=click.INT, required=True, help="Location of the environment configuration file.")
def run(host: str, port: int) -> None:
    """
    Run the socket server.
    Command starts the socket server with the specified host and port.
    Handles server startup and graceful shutdown on interruption.

    Args:
        host (str): The host the server is running on.
        port (int): The port the server is listening on.
    """
    # pylint: disable=C0415
    from sockets import CONN_COUNT_FILE, PID_FILE
    from sockets.async_server import AsyncSocketServer

    server = AsyncSocketServer(host, port)
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Stop server listening on %s:%d by pressing Ctrl+C", host, port)
    except Exception as e:
        logger.error("Error %s occurred while starting server on %s:%d", str(e), host, port)
    finally:
        if pathlib.Path(CONN_COUNT_FILE).exists():
            os.remove(CONN_COUNT_FILE)
        if pathlib.Path(PID_FILE).exists():
            os.remove(PID_FILE)


@click.command()
def stop() -> None:
    """
    Gracefully stop the running socket server by sending a SIGTERM signal.

    This command retrieves the PID of the running server and sends a SIGTERM signal
    to stop the server gracefully. If any error occurs (e.g., invalid PID, permission issues),
    an appropriate message is logged.
    """
    # pylint: disable=C0415
    from sockets import CONN_COUNT_FILE, ENCODING, PID_FILE

    server_pid_file = pathlib.Path(PID_FILE)

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
        if pathlib.Path(CONN_COUNT_FILE).exists():
            os.remove(CONN_COUNT_FILE)
        if pathlib.Path(PID_FILE).exists():
            os.remove(PID_FILE)


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
    is_flag=True,
    default=True,
    show_default=True,
    help="Show last lines in the log file. If False show first lines.",
)
@click.option("--follow", "-f", is_flag=True, default=False, show_default=True, help="Follow the logs.")
def logs(lines_count: int = 0, last: bool = True, follow: bool = False) -> None:
    """
    Display the content of the most recent log file, considering log rotation.

    This command allows users to view log files, either in their entirety or partially,
    and follow the logs in real time if needed.

    Args:
        lines_count (int): Number of lines in the log to display. Defaults to 0 (all lines).
        last (bool): If True, display the last lines of the log file, otherwise display the first lines.
        follow (bool): If True, follow the logs as they are written (like `tail -f`).
    """
    # pylint: disable=C0415
    from logs.logging_conf import server_logging_dir
    from sockets import ENCODING

    logs_dir = pathlib.Path(server_logging_dir)

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
    Show the current number of connections to the server.
    This command reads the connection count from the appropriate file and displays it.
    """
    # pylint: disable=C0415
    from sockets import CONN_COUNT_FILE, ENCODING

    conn_count_file = pathlib.Path(CONN_COUNT_FILE)
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


@click.group()
def cli_web() -> None:
    """
    CLI entrypoint for web application.
    """


@click.command()
@click.option("--host", "-h", type=click.STRING, show_default=True, default="0.0.0.0", help="Server host.")
@click.option("--port", "-p", type=click.INT, show_default=True, default="8000", help="Server port.")
@click.option("--workers", type=click.INT, show_default=True, default="2", help="Number of worker processes.")
@click.option("--env-file", type=click.Path(exists=True), required=True, help="Environment configuration file.")
def runserver(workers: int, host: str, port: int, env_file: pathlib.Path) -> None:
    """
    Run the FastAPI server using uvicorn with the specified options.

    Args:
        workers (int): Number of worker processes for handling requests.
        env_file (Optional[pathlib.Path]): Path to the environment configuration file.
        host (str): The server host address.
        port (int): The port to bind the server.

    This command sets up and runs the FastAPI server with configurable settings such as
    host, port, and workers. It also optionally reads an environment configuration file if specified.
    """
    config = {
        "app": "main:app",
        "host": host,
        "port": port,
        "workers": workers,
        "env_file": env_file,
    }

    uvicorn.run(**{key: value for key, value in config.items() if value is not None})


cli_web.add_command(runserver)
