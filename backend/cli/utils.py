import os
from io import StringIO
from typing import Sequence

import click
import requests
import requests.auth
from dotenv import load_dotenv
from fastapi import status
from requests.auth import HTTPBasicAuth
from sqlalchemy import Row, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from users.schemas import HashType


class EngineSingleton:
    """
    Singleton class to manage the database engine instance.
    Ensures only one instance of the engine is created and provides methods
    to reset and retrieve the engine.
    """

    _instance: Engine | None = None

    @classmethod
    def get_instance(cls) -> Engine:
        """
        Get the singleton instance of the database engine.
        If the engine is not initialized, it initializes it first.

        Returns:
            Engine: The database engine instance.
        """
        if cls._instance is None:
            from db_connection import engine  # pylint: disable=C0415

            cls._instance = engine
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance of the database engine to None,
        allowing it to be re-initialized when needed.
        """
        cls._instance = None


def load_env_in_memory(content: str) -> None:
    """
    Load environment variables from a string content into memory
    and reset the database engine instance.

    Args:
        content (str): The content of the environment file.
    """
    env_file_io = StringIO(content)
    load_dotenv(stream=env_file_io)
    EngineSingleton.reset_instance()


def load_env_in_shell_env(path: str) -> None:
    """
    Load environment variables from a file path into the shell's environment
    and reset the database engine instance.

    Args:
        path (str): The file path to the environment file.
    """
    os.environ["ENV_FILE_PATH"] = path
    EngineSingleton.reset_instance()


def fetch_env_file(url: str, username: str, password: str) -> str:
    """
    Fetches the .env file content from a specified URL.

    Function sends a GET request to the provided URL to fetch the content of an
    environment file. If authentication is required, it will use the provided username
    and password.

    Args:
        url (str): The URL pointing to the .env file.
        username (str): The username for basic authentication.
        password (str): The password for basic authentication.

    Raises:
        click.Abort: If the request fails or the response status is not 200 OK.

    Returns:
        str: The content of the fetched .env file.
    """
    basic_auth = HTTPBasicAuth(username, password)
    response = requests.get(url, auth=basic_auth, timeout=5)
    if response.status_code == status.HTTP_200_OK:
        return response.text

    click.echo(f"Failed to fetch .env file: {response.status_code}")
    raise click.Abort()


def get_proxy_credentials_from_db(users_emails: list[str]) -> Sequence[Row[tuple[str, str, str]]]:
    """
    Fetch proxy credentials for the given list of users emails from database.

    Args:
        users_emails (list[str]): List of user email addresses.

    Returns:
        Sequence[Row[tuple[str, str, str]]]: List of tuples containing proxy login, hashed password,
            and password hash type.
    """
    # pylint: disable=C0415
    # pylint: disable=W0611
    from users.models import User

    engine = EngineSingleton.get_instance()
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
    Build a list of formatted proxy credentials for a configuration file.

    The function generates the formatted credential strings for each user based on their hash type,
    ready to be written to a configuration file.

    Args:
        creds_from_db (Sequence[Row[tuple[str, str, str]]]):
            A sequence of database rows where each row is a tuple containing:
            - login (str): The proxy login bind to the user.
            - hashed password (str): The proxy hashed password bind to the user.
            - password hash type (str): The type of password hash used (e.g., MD5, SHA256).
        users_emails (list[str]):
            A list of user email addresses corresponding to the database rows.

    Raises:
        ValueError: If any user's login or password is `None`.

    Returns:
        str: A string containing the formatted credentials, where each credential is a line in the format:
            - For plain (CL) passwords: {login}:CL:{hashed_password}
            - For crypt (CR) passwords (e.g., MD5 or SHA256): "{login}:CR:{hashed_password}"
            The resulting string ends with a newline character.
    """
    users_emails.sort()
    config_proxy_credentials: dict[str, dict[str, str]] = {
        email: {"login": cred[0], "password": cred[1], "password_type": cred[2]}
        for cred, email in zip(creds_from_db, users_emails)
    }

    file_lines: list[str] = []
    for email, conf in config_proxy_credentials.items():
        if conf["login"] is None and conf["password"] is None:
            raise ValueError(
                f"Proxy login and proxy password must not be None. Check proxy credentials for user with email: {email}."
            )
        if conf["password_type"] is None:
            file_lines.append(f"{conf['login']}:CL:{conf['password']}")
        elif conf["password_type"] in {HashType.MD5, HashType.SHA256}:
            file_lines.append(f'"{conf["login"]}:CR:{conf["password"]}"')

    if len(file_lines) == 1:
        return f"{file_lines[0]}\n"

    return "\n".join(file_lines) + "\n"
