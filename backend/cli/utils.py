import click
import requests
from fastapi import status


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
    response = requests.get(url, auth=(username, password), timeout=5)
    if response.status_code == status.HTTP_200_OK:
        return response.text

    click.echo(f"Failed to fetch .env file: {response.status_code}")
    raise click.Abort()
