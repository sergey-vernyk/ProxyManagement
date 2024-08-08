from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.client import ResponseEnum
from huawei_lte_api.exceptions import (LoginErrorInvalidCredentialsException,
                                       ResponseErrorException)


def reboot_modem(url: str, username: str | None, password: str | None) -> str:
    """
    Attempts to reboot a modem at the specified `url` using the provided credentials.

    Args:
        url (str): The URL of the modem to be rebooted.
        username (str | None): The username for authentication, or None if no username is required.
        password (str | None): The password for authentication, or None if no password is required.

    Returns:
        str: A message indicating the result of the reboot attempt:
            - 'Rebooted' if the modem was successfully rebooted.
            - 'Not rebooted' if the modem was not rebooted due to a non-OK response.
            - 'Error: <exception message>' if an exception occurred during the process,
              including issues with credentials, response errors, or any other connection issues.

    Raises:
        LoginErrorInvalidCredentialsException: If the credentials provided are invalid or authentication fails.
        ResponseErrorException: If there is an issue with the response from the modem,
            such as an unexpected response or connection error.
    """
    try:
        with Connection(url, username, password) as connection:
            client = Client(connection)
            result = "Rebooted" if client.device.reboot() == ResponseEnum.OK.value else "Not rebooted"
    except (LoginErrorInvalidCredentialsException, ResponseErrorException) as e:
        return f"Error: {e}"

    return result
