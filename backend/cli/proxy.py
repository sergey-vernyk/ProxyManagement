import os
import pathlib
from typing import Sequence

import click
from db_connection import engine
from sqlalchemy import Row, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from tabulate import tabulate
from users.schemas import HashType


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


@click.group(help="CLI for making CRUD operations for user proxy credentials.")
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    required=True,
    help="Location of the environment configuration file.",
)
def cli_proxy(env_file: pathlib.Path) -> None:
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


cli_proxy.add_command(create_user_list)
cli_proxy.add_command(insert_into_user_list)
cli_proxy.add_command(get_from_user_list)
cli_proxy.add_command(delete_from_user_list)
