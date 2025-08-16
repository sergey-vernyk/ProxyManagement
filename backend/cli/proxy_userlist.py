import pathlib

import click
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from tabulate import tabulate

from db_connection import engine

from .schemas import EnvPathOrEnvUrl
from .utils import (
    build_credentials_for_config,
    fetch_env_file,
    get_proxy_credentials_from_db,
    load_env_in_memory,
    load_env_in_shell_env,
)


@click.group(help="CLI for making CRUD operations for user proxy credentials.")
@click.option(
    "--env-file",
    type=click.STRING,
    required=True,
    help="Location or URL of the environment configuration file.",
)
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
def cli_proxy_userlist(ctx: click.Context, env_file: str, username: str | None, password: str | None) -> None:
    """
    CLI entrypoint for interacting with proxy credentials for a user.

    Loads the environment variables from the provided file.

    Args:
        ctx (click.Context): Click context object for passing information across commands.
        env_file (str): Path to the environment configuration file.
        username (str | None): Username for authentication if the env_file is a URL.
        password (str | None): Password for authentication if the env_file is a URL.
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


@click.command(help="Create a user list file with proxy credentials.")
@click.argument("filename", type=click.Path())
@click.argument("users", type=click.STRING)
@click.pass_context
def create_user_list(ctx: click.Context, filename: pathlib.Path, users: str) -> None:
    """
    Create a user list file with proxy credentials based on user emails.

    Args:
        ctx (click.Context): Click context object for passing information across commands.
        filename (pathlib.Path): The path to the file where user credentials will be saved.
        users (str): A comma-separated string of user email addresses.

    This command creates a new file with proxy credentials for the specified users.
    If the file already exists, it will not overwrite it.
    """
    if not ctx.obj["ENV_VALID"]:
        return

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

    # pylint: disable=import-outside-toplevel
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

    try:
        file_lines = build_credentials_for_config(db_users_proxy_credentials, users_emails)
        filename.write_text(file_lines, encoding)
    except PermissionError:
        click.echo(click.style(f"Error: Permission denied to write to: {filename}", fg="red", bold=True))
    except UnicodeEncodeError:
        click.echo(
            click.style(
                "Error: Could not encode the file with the provided encoding.",
                fg="red",
                bold=True,
            )
        )
    except ValueError as e:
        click.echo(click.style(str(e), bold=True, fg="red"))
    else:
        click.echo(
            click.style(
                f"{len(users_emails)} credential(s) has been added into the created users list.",
                bold=True,
                fg="green",
            )
        )


@click.command(help="Insert new user credentials into the user list file.")
@click.argument("filename", type=click.Path(exists=True))
@click.argument("users", type=click.STRING)
@click.pass_context
def insert_into_user_list(ctx: click.Context, filename: pathlib.Path, users: str) -> None:
    """
    Insert new user credentials into the user list file if they don't already exist.

    Args:
        ctx (click.Context): Click context object for passing information across commands.
        filename (pathlib.Path): Path to the configuration file where user credentials will be added.
        users (str): Comma-separated list of user emails for which credentials should be inserted.
    """
    if not ctx.obj["ENV_VALID"]:
        return

    # ensure that filename is a path not str
    filename = pathlib.Path(filename)
    # pylint: disable=import-outside-toplevel
    from config import get_settings

    encoding = get_settings().default_encoding
    try:
        users_emails = users.split(",")
        db_users_proxy_credentials = get_proxy_credentials_from_db(users_emails)
    except SQLAlchemyError as e:
        click.echo(click.style(f"Database error: {e}", fg="red", bold=True))
        return

    try:
        file_lines = build_credentials_for_config(db_users_proxy_credentials, users_emails)
        with open(filename, encoding=encoding) as file:
            existing_lines = {line.strip() for line in file.readlines()}

        duplicate_lines = [line for line in file_lines.split("\n") if line.strip() in existing_lines]
        if duplicate_lines:
            click.echo(click.style("Config line is already exists. Aborting...", fg="red", bold=True))
            return

        click.confirm(
            click.style(
                f"Are you sure for ADDING new lines in the '{filename}'?",
                fg="green",
                bold=True,
            ),
            abort=True,
        )

        with open(filename, mode="a", encoding=encoding) as file:
            file.write(file_lines)

        lines_inserted: int = len([line for line in file_lines.split("\n") if line.strip()])

    except PermissionError:
        click.echo(click.style(f"Error: Permission denied to write to: {filename}", fg="red", bold=True))
    except UnicodeEncodeError:
        click.echo(
            click.style(
                "Error: Could not encode the file with the provided encoding.",
                fg="red",
                bold=True,
            )
        )
    except ValueError as e:
        click.echo(click.style(str(e), bold=True, fg="red"))
    else:
        click.echo(
            click.style(
                f"{lines_inserted} credential(s) have been inserted.",
                fg="green",
                bold=True,
            ),
        )


@click.command(help="Display user credentials from the user list file.")
@click.argument("filename", type=click.Path(exists=True))
@click.pass_context
def get_from_user_list(ctx: click.Context, filename: pathlib.Path) -> None:
    """
    Display user credentials from the user list file and their corresponding emails and hash types.

    Args:
        ctx (click.Context): Click context object for passing information across commands.
        filename (pathlib.Path): Path to the configuration file where user credentials are stored.
    """
    if not ctx.obj["ENV_VALID"]:
        return

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
        click.echo(
            click.style(
                "Error: Could not encode the file with the provided encoding.",
                fg="red",
                bold=True,
            )
        )

    # pylint: disable=unused-import
    from auth.otp.models import OTP  # noqa: F401
    from modems.models import Modem  # noqa: F401
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
@click.pass_context
def delete_from_user_list(ctx: click.Context, filename: pathlib.Path, users: str) -> None:
    """
    Delete user credentials from the user list file.

    Args:
        ctx (click.Context): Click context object for passing information across commands.
        filename (pathlib.Path): Path to the configuration file where user credentials are stored.
        users (str): Comma-separated list of user emails for which credentials should be deleted.
    """
    if not ctx.obj["ENV_VALID"]:
        return

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
        click.echo(
            click.style(
                "Error: Could not encode the file with the provided encoding.",
                fg="red",
                bold=True,
            )
        )
    except PermissionError:
        click.echo(click.style(f"Error: Permission denied to write to: {filename}", fg="red", bold=True))
    else:
        click.echo(
            click.style(
                f"{creds_to_delete} credential(s) have been deleted.",
                fg="green",
                bold=True,
            ),
        )


cli_proxy_userlist.add_command(create_user_list)
cli_proxy_userlist.add_command(insert_into_user_list)
cli_proxy_userlist.add_command(get_from_user_list)
cli_proxy_userlist.add_command(delete_from_user_list)
