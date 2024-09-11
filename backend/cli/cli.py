import asyncio
import os
import pathlib
import signal
import time
from datetime import datetime
from typing import Sequence

import click
import uvicorn
from db_connection import engine
from logs.logging_conf import get_socket_server_logger
from sqlalchemy import select
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from tabulate import tabulate
from users.schemas import HashType

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


def get_proxy_credentials_from_db(users_emails: list[str]) -> Sequence[Row[tuple[str, str, str]]]:
    """
    Fetch proxy credentials for a list of user emails from database.

    Args:
        users_emails (list[str]): List of user email addresses.

    Returns:
        Sequence[Row[tuple[str, str, str]]]: List of tuples containing proxy login, hashed password,
            and password hash type.
    """
    # pylint: disable=C0415
    # pylint: disable=W0611
    from auth.otp.models import OTP
    from modems.models import Modem
    from users.models import User

    try:
        with Session(engine) as session:
            return session.execute(
                select(User.proxy_login, User.proxy_password_hashed, User.proxy_password_hash_type)
                .where(User.email.in_(users_emails))
                .order_by(User.email)
            ).fetchall()
    except SQLAlchemyError as e:
        raise e


def build_credentials_for_config(creds_from_db: Sequence[Row[tuple[str, str, str]]], users_emails: list[str]) -> str:
    """
    Build a list of formatted credentials for a configuration file from database results.

    Args:
        creds_from_db (Sequence[Row[tuple[str, str, str]]]):
            Sequence of database rows containing login, hashed password, and password hash type.
        users_emails (list[str]):
            List of user email addresses corresponding to the database results.

    Returns:
        str: A string containing formatted user credentials separated by newlines,
            ready to be written to a config file.
    """
    users_emails.sort()
    config_proxy_credentials: dict[str, dict[str, str]] = {
        email: {"login": cred[0], "password": cred[1], "password_type": cred[2]}
        for cred, email in zip(creds_from_db, users_emails)
    }

    file_lines: list[str] = []
    for conf in config_proxy_credentials.values():
        if conf["password_type"] is None:
            file_lines.append(f"{conf['login']}:CL:{conf['password']}")
        elif conf["password_type"] in {HashType.MD5, HashType.SHA256}:
            file_lines.append(f'"{conf["login"]}:CR:{conf["password"]}"')

    return "\n".join(file_lines)


@click.group()
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    required=True,
    help="Location of the environment configuration file.",
)
def proxy(env_file: pathlib.Path) -> None:
    """
    CLI entrypoint for proxy configuration.

    Loads the environment variables from the provided file.

    Args:
        env_file (pathlib.Path): Path to the environment configuration file.
    """
    os.environ["ENV_FILE_PATH"] = str(env_file)


@click.command(help="Create a user list file with proxy credentials.")
@click.argument("filename", type=click.Path())
@click.argument("users", type=click.STRING)
def create_user_list(filename: pathlib.Path, users: str) -> None:
    """
    Create a user list file with proxy credentials based on user emails.

    Args:
        filename (pathlib.Path): The path to the file where user credentials will be saved.
        users (str): A comma-separated string of user email addresses.

    This command creates a new file with proxy credentials for the specified users.
    If the file already exists, it will not overwrite it.
    """
    # ensure that filename is a path not str
    filename = pathlib.Path(filename)
    if filename.exists():
        click.echo(
            click.style(
                "This command forbids updating an existing file. Use the 'insert-into-user-list' command instead.",
                fg="red",
                bold=True,
            )
        )
        return

    # pylint: disable=C0415
    from config import get_settings

    encoding = get_settings().default_encoding
    try:
        users_emails = users.split(",")
        db_users_proxy_credentials = get_proxy_credentials_from_db(users_emails)
    except SQLAlchemyError as e:
        click.echo(click.style(f"Database error: {e}", fg="red", bold=True))
        return

    if len(db_users_proxy_credentials) != len(users_emails):
        click.echo(
            click.style(
                "Some users with the given emails does not exists. Check provided emails.",
                fg="red",
                bold=True,
            )
        )
        return

    file_lines = build_credentials_for_config(db_users_proxy_credentials, users_emails)
    try:
        filename.write_text(file_lines, encoding)
    except PermissionError:
        click.echo(click.style(f"Error: Permission denied to write to: {filename}", fg="red", bold=True))
    except UnicodeEncodeError:
        click.echo(click.style("Error: Could not encode the file with the provided encoding.", fg="red", bold=True))


@click.command(help="Insert new user credentials into the user list file.")
@click.argument("filename", type=click.Path(exists=True))
@click.argument("users", type=click.STRING)
def insert_into_user_list(filename: pathlib.Path, users: str) -> None:
    """
    Insert new user credentials into the user list file if they don't already exist.

    Args:
        filename (pathlib.Path): Path to the configuration file where user credentials will be added.
        users (str): Comma-separated list of user emails for which credentials should be inserted.
    """
    # ensure that filename is a path not str
    filename = pathlib.Path(filename)

    # pylint: disable=C0415
    from config import get_settings

    encoding = get_settings().default_encoding
    try:
        users_emails = users.split(",")
        db_users_proxy_credentials = get_proxy_credentials_from_db(users_emails)
    except SQLAlchemyError as e:
        click.echo(click.style(f"Database error: {e}", fg="red", bold=True))
        return

    file_lines = build_credentials_for_config(db_users_proxy_credentials, users_emails)
    lines_inserted = 0
    try:
        with open(filename, encoding=encoding) as file:
            existing_lines = {line.strip() for line in file.readlines()}

        duplicate_lines = [line for line in file_lines.split("\n") if line.strip() in existing_lines]
        if duplicate_lines:
            click.echo(click.style("Config line is already exists. Aborting...", fg="red", bold=True))
            return

        click.confirm(
            click.style(f"Are you sure for ADDING new lines in the '{filename}'?", fg="green", bold=True),
            abort=True,
        )

        with open(filename, mode="a", encoding=encoding) as file:
            file.write(file_lines)

        lines_inserted: int = len(list(file_lines.split("\n")))

    except PermissionError:
        click.echo(click.style(f"Error: Permission denied to write to: {filename}", fg="red", bold=True))
    except UnicodeEncodeError:
        click.echo(click.style("Error: Could not encode the file with the provided encoding.", fg="red", bold=True))

    click.echo(
        click.style(f"{lines_inserted} credential(s) have been inserted.", fg="green", bold=True),
    )


@click.command(help="Display user credentials from the user list file.")
@click.argument("filename", type=click.Path(exists=True))
def get_from_user_list(filename: pathlib.Path) -> None:
    """
    Display user credentials from the user list file and their corresponding emails and hash types.

    Args:
        filename (pathlib.Path): Path to the configuration file where user credentials are stored.
    """
    # ensure that filename is a path not str
    filename = pathlib.Path(filename)

    # pylint: disable=C0415
    from config import get_settings

    encoding = get_settings().default_encoding
    creds_from_file = ""
    try:
        with open(filename, encoding=encoding) as file:
            creds_from_file = file.read()
    except UnicodeEncodeError:
        click.echo(click.style("Error: Could not encode the file with the provided encoding.", fg="red", bold=True))

    # pylint: disable=C0415
    # pylint: disable=W0611
    from auth.otp.models import OTP
    from modems.models import Modem
    from users.models import User

    # credential config file looks like "X1C-HpxeWHnsdup2tie:CR:$1$5Cb2O1Da$r/BJBfSGuQt4it9ASUJiI/"
    # or kfwiecw:CL:kjnoepmcp" without double quotes (")
    logins = [cred.strip('"').split(":")[0] for cred in creds_from_file.split("\n")]
    try:
        with Session(engine) as session:
            emails_hash_type = session.execute(
                select(User.email, User.proxy_password_hash_type)
                .where(User.proxy_login.in_(logins))
                .order_by(User.email)
            ).fetchall()
    except SQLAlchemyError as e:
        click.echo(click.style(f"Database error: {e}", fg="red", bold=True))
        return

    headers = ("Email", "Credentials", "Hash Type")
    table: list[list[str]] = [
        [email, cred.strip('"'), hash_type.value]
        for (email, hash_type), cred in zip(emails_hash_type, creds_from_file.split("\n"))
    ]

    click.echo(tabulate(table, tablefmt="pretty", headers=headers))


@click.command(help="Delete user credentials from the user list file.")
@click.argument("filename", type=click.Path(exists=True))
@click.argument("users", type=click.STRING)
def delete_from_user_list(filename: pathlib.Path, users: str) -> None:
    """
    Delete user credentials from the user list file.

    Args:
        filename (pathlib.Path): Path to the configuration file where user credentials are stored.
    """
    # ensure that filename is a path not str
    filename = pathlib.Path(filename)

    # pylint: disable=C0415
    from config import get_settings

    encoding = get_settings().default_encoding
    try:
        users_emails = users.split(",")
        db_users_proxy_credentials = get_proxy_credentials_from_db(users_emails)
    except SQLAlchemyError as e:
        click.echo(click.style(f"Database error: {e}", fg="red", bold=True))
        return

    if len(db_users_proxy_credentials) != len(users_emails):
        click.echo(
            click.style(
                "Some users with the given emails does not exists. Check provided emails.",
                fg="red",
                bold=True,
            )
        )
        return

    proxy_logins: set[str] = {cred[index] for index, cred in enumerate(db_users_proxy_credentials)}
    creds_to_delete = 0

    try:
        with open(filename, "r+", encoding=encoding) as file:
            creds_from_file = file.readlines()
            # filter out the credentials that are in proxy_logins
            remaining_creds = [cred for cred in creds_from_file if cred.strip('"').split(":")[0] not in proxy_logins]
            creds_to_delete: int = len(creds_from_file) - len(remaining_creds)
            if not creds_to_delete:
                click.echo(
                    click.style(
                        f"No credentials were found corresponds by provided email(s) to delete from the '{filename}'.",
                        fg="red",
                        bold=True,
                    ),
                )
                return

            click.confirm(
                click.style(
                    f"Are you sure for DELETING {creds_to_delete} credential(s) from '{filename}'?",
                    fg="red",
                    bold=True,
                ),
                abort=True,
            )
            file.seek(0)  # move file pointer to the beginning of the file to overwrite it
            file.writelines(remaining_creds)
            file.truncate()
    except UnicodeEncodeError:
        click.echo(click.style("Error: Could not encode the file with the provided encoding.", fg="red", bold=True))
    except PermissionError:
        click.echo(click.style(f"Error: Permission denied to write to: {filename}", fg="red", bold=True))

    click.echo(
        click.style(f"{creds_to_delete} credential(s) have been deleted.", fg="green", bold=True),
    )


proxy.add_command(create_user_list)
proxy.add_command(insert_into_user_list)
proxy.add_command(get_from_user_list)
proxy.add_command(delete_from_user_list)
