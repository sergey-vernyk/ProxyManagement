"""
Module provides settings for socket server and socket client.
"""

import logging
from datetime import datetime
from pathlib import Path

from config import get_settings

settings = get_settings()
ENCODING = settings.default_encoding

server_logging_dir = Path(__file__).parent / "server_logs"
client_logging_dir = Path(__file__).parent / "client_logs"

if not server_logging_dir.exists():
    server_logging_dir.mkdir()

if not client_logging_dir.exists():
    client_logging_dir.mkdir()


def get_server_logger() -> logging.Logger:
    """
    Returns logger using for socket server logging.
    """
    logger = logging.getLogger("socket_server")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s - lino: %(lineno)d", "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(server_logging_dir / f"{datetime.now().date()}.log", encoding=ENCODING)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def get_client_logger() -> logging.Logger:
    """
    Returns logger using for socket client logging.

    Returns:
        logging.Logger: _description_
    """
    logger = logging.getLogger("socket_client")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s - lino: %(lineno)d", "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(client_logging_dir / f"{datetime.now().date()}.log", encoding=ENCODING)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger
