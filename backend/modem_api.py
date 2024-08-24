from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.client import ResponseEnum
from huawei_lte_api.enums.device import ControlModeEnum
from huawei_lte_api.exceptions import (LoginErrorInvalidCredentialsException,
                                       ResponseErrorException)


def reboot_modem(url: str, username: str | None, password: str | None) -> bool | str:
    """
    Attempts to reboot a modem at the specified `url` using the provided credentials.

    Args:
        url (str): The URL of the modem to be rebooted.
        username (str | None): The username for authentication, or None if no username is required.
        password (str | None): The password for authentication, or None if no password is required.

    Returns:
        bool | str: The result of the reboot attempt:
            - True if the modem was successfully rebooted.
            - False if the modem was not rebooted due to a non-OK response.
            - A string in the format 'Error: <exception message>' if an exception occurred during the process,
              such as issues with credentials, response errors, or any other connection issues.

    Raises:
        LoginErrorInvalidCredentialsException: If the provided credentials are invalid or authentication fails.
        ResponseErrorException: If there is an issue with the modem's response,
            such as an unexpected response or connection error.
        ConnectionError: If there is a problem establishing a connection to the modem.
    """
    try:
        with Connection(url, username, password) as connection:
            client = Client(connection)
            result = client.device.set_control(ControlModeEnum.REBOOT) == ResponseEnum.OK.value
    except (LoginErrorInvalidCredentialsException, ResponseErrorException) as e:
        return f"Error: {e}"

    return result
