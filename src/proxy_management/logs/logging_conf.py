"""
Module provides logger settings for socket server, socket client and endpoints.
"""

import logging
import logging.handlers
from datetime import datetime
from typing import Any

from fastapi import Request

from . import client_logging_dir, endpoint_logging_dir, server_logging_dir, settings

ENCODING = settings.default_encoding


def build_ip_address_for_log(ip_addr: str | None) -> str:
    """
    Formats the given IP address for logging.

    Args:
        ip_addr (str | None): The initial IP address as a string, or None if
            no IP address is available.

    Returns:
        str: The formatted IP address in the format '192.168.x.x' if a valid
            IP is provided, or '---.---.---.---' if no IP address is supplied.

    Raises:
        ValueError: If the provided IP address does not consist of 4 octets
            (e.g., '127.0.0.1' is valid, while '127.0.1' is not).
    """
    if ip_addr is not None:
        ip_addr_octets = ip_addr.split(".")
        if len(ip_addr_octets) == 4:
            return f"{ip_addr_octets[0]}.{ip_addr_octets[1]}.x.x"

        raise ValueError("IP address must have 4 octets. E.g. 127.0.0.1")

    return "---.---.---.---"


def build_logger_extra_data(request: Request, **kwargs: str | Any) -> dict[str, Any]:
    """
    Builds and returns extra data for logging purposes, including the client's IP address
    and other information if any.


    Args:
        request (Request): HTTP request.
        **kwargs: Additional keyword arguments to include in the logger data.

    Returns:
        dict[str, Any]: A dictionary containing:
            - `client_ip` (str or None): The client's IP address if available, otherwise None.
            - Any additional data passed through `kwargs`.
    """
    return {
        "client_ip": build_ip_address_for_log(request.client.host) if request.client is not None else None,
        **kwargs,
    }


def get_socket_server_logger() -> logging.Logger:
    """
    Returns logger using for socket server logging.
    """
    logger = logging.getLogger("socket_server")
    if not logger.hasHandlers():  # Check if handlers are already set
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s - lino: %(lineno)d", "%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.handlers.RotatingFileHandler(
            server_logging_dir / f"{datetime.now().date()}.log",
            encoding=ENCODING,
            maxBytes=settings.max_bytes_log_rotating,
            backupCount=settings.backup_count,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_socket_client_logger() -> logging.Logger:
    """
    Returns logger using for socket client logging.
    """
    logger = logging.getLogger("socket_client")
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s - lino: %(lineno)d", "%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.handlers.RotatingFileHandler(
            client_logging_dir / f"{datetime.now().date()}.log",
            encoding=ENCODING,
            maxBytes=settings.max_bytes_log_rotating,
            backupCount=settings.backup_count,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_endpoint_logger() -> logging.Logger:
    """
    Returns logger using in endpoints.
    """
    logger = logging.getLogger("endpoint")
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "{client_ip} - {asctime} - {levelname} - {message} [{module_name}.{func_name}():{lineno}]",
            "%Y-%m-%d %H:%M:%S",
            style="{",
        )
        file_handler = logging.handlers.RotatingFileHandler(
            endpoint_logging_dir / f"{datetime.now().date()}.log",
            encoding=ENCODING,
            maxBytes=settings.max_bytes_log_rotating,
            backupCount=settings.backup_count,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
