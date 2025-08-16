import asyncio
import logging
import os
import pathlib
import signal
import time
from datetime import datetime

import click
from pydantic import ValidationError

from .schemas import EnvPathOrEnvUrl
from .utils import fetch_env_file, load_env_in_memory, load_env_in_shell_env


@click.group(
    help=(
        "CLI provides functionality to start the socket server, stop the server, show its logs and accepted connections."
    )
)
@click.argument("env_file", type=click.STRING)
@click.option(
    "--username",
    "-u",
    type=click.STRING,
    required=False,
    help="Username for authenticating if the provided 'env_file' is URL.",
)
@click.option(
    "--password",
    "-pass",
    type=click.STRING,
    required=False,
    help="Password for authenticating if the provided 'env_file' is URL.",
)
@click.pass_context
def cli_socket_server(ctx: click.Context, env_file: str, username: str | None, password: str | None) -> None:
    """
    CLI entry point for socket server operations.

    Loads the environment variables from the provided file (either a local file or a URL).
    Handles validation and ensures that necessary environment variables are available
    before running any further commands.

    Args:
        ctx (click.Context): The context object that can be used to pass information between commands.
        env_file (str): Path to the environment configuration file or URL.
        username (str, optional): Username for authentication if 'env_file' is a URL.
        password (str, optional): Password for authentication if 'env_file' is a URL.
    """
    ctx.ensure_object(dict)
    try:
        path_or_url = EnvPathOrEnvUrl(env_file_or_url=env_file)
    except ValidationError as e:
        click.echo(f"Invalid input: {e}")
        ctx.obj["ENV_VALID"] = False
        return

    ctx.obj["ENV_VALID"] = True

    if "http" in path_or_url.env_file_or_url:
        if username is None or password is None:
            click.echo(
                click.style(
                    "Username and password must be provided if param 'env_file' is URL.",
                    bold=True,
                    fg="red",
                )
            )
            raise click.Abort()

        env_file_content = fetch_env_file(path_or_url.env_file_or_url, username, password)
        load_env_in_memory(env_file_content)
    else:
        load_env_in_shell_env(env_file)
    # pylint: disable=C0415
    from logs.logging_conf import get_socket_server_logger

    logger = get_socket_server_logger()
    ctx.obj["logger"] = logger


@click.command(help="Run the socket server with provided host and port.")
@click.option(
    "--host",
    "-h",
    type=click.STRING,
    required=True,
    default="localhost",
    show_default=True,
    help="The host the server is running on.",
)
@click.option(
    "--port",
    "-p",
    type=click.INT,
    required=True,
    help="Location of the environment configuration file.",
)
@click.pass_context
def run(ctx: click.Context, host: str, port: int) -> None:
    """
    Starts the socket server with the specified host and port.

    Command initializes the socket server and starts it with the provided
    host and port settings.

    Args:
        ctx (click.Context): The context object passed from the parent command,
            which contains environment validation info and logger.
        host (str): The host on which the server will run.
        port (int): The port on which the server will listen.
    """
    if not ctx.obj["ENV_VALID"]:
        return

    logger: logging.Logger = ctx.obj["logger"]
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


@click.command(help="Stop the running socket server.")
@click.pass_context
def stop(ctx: click.Context) -> None:
    """
    Gracefully stop the running socket server by sending a SIGTERM signal.

    This command stops the running socket server by reading the server's PID from the PID file
    and sending a SIGTERM signal to gracefully terminate the process.
    If the PID file is missing, or the server is not running, appropriate
    error messages are logged and displayed.

    Args:
        ctx (click.Context): The context object that holds the environment validation state
            and logger instance passed from the parent command.
    """
    if not ctx.obj["ENV_VALID"]:
        return

    logger: logging.Logger = ctx.obj["logger"]  # pylint: disable=W0621

    from sockets import CONN_COUNT_FILE, ENCODING, PID_FILE  # pylint: disable=C0415

    server_pid_file = pathlib.Path(PID_FILE)

    if not server_pid_file.exists():
        logger.error("PID file not found. Probably, socket server isn't running.")
        click.echo(
            click.style(
                "PID file not found. Probably, socket server isn't running.\n"
                "Use 'run -h <host> -p <port>' to run the server.",
                fg="red",
                bold=True,
            )
        )
        return

    try:
        pid = int(server_pid_file.read_text(encoding=ENCODING).strip())

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


@click.command(help="Show logs for the socket server.")
@click.option(
    "--lines-count",
    "-lc",
    type=click.INT,
    default=0,
    show_default=True,
    help="Show number of lines in the log. If 0 show all lines.",
)
@click.option("--last", "-l", is_flag=True, help="Show last lines in the log file.")
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
            key=lambda log: (
                datetime.strptime(log.split(".")[0], "%Y-%m-%d"),
                log.split(".")[1],
            ),
        ).pop()

        last_log_file = logs_dir / last_log_name
    except (FileNotFoundError, ValueError, IndexError) as e:
        click.echo(click.style(f"Error finding or reading log files: {e}", fg="red", bold=True))
        return

    if last_log_file.exists():
        with open(last_log_file, encoding=ENCODING) as file:
            if not follow:
                lines = file.readlines()
                # show all log lines
                if not lines_count:
                    log_lines = [click.style(line, fg="cyan", bold=True) for line in lines]
                # show number of lines defined in `lines_count` variable
                else:
                    slice_lines = slice(-lines_count, None, None) if last else slice(None, lines_count, None)
                    log_lines = [click.style(line, fg="cyan", bold=True) for line in lines[slice_lines]]

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
                    click.echo(
                        click.style(
                            "Interrupt following logs by pushing Ctrl+C.",
                            bold=True,
                            fg="red",
                        )
                    )
    else:
        click.echo(click.style("Log file not found.", fg="red", bold=True))


@click.command(help="Show the current numbers of accepted connection to the socket server.")
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
        click.echo(
            click.style(
                f"Current number of connection to the server is {conn_number}.",
                bold=True,
                fg="cyan",
            )
        )
    else:
        click.echo(
            click.style(
                "The server has not accepted any connection from client yet.",
                bold=True,
                fg="red",
            )
        )


cli_socket_server.add_command(run)
cli_socket_server.add_command(stop)
cli_socket_server.add_command(logs)
cli_socket_server.add_command(connection_number)
