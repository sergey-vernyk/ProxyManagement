"""
Module provides logger settings for socket server, socket client and endpoints.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

from config import get_settings

settings = get_settings()
ENCODING = settings.default_encoding

# server_logging_dir = Path(__file__).parent / "server_logs"
# client_logging_dir = Path(__file__).parent / "client_logs"
# endpoint_logging_dir = Path(__file__).parent / "endpoints_logs"

server_logging_dir = Path(r"C:\proxy") / "server_logs"
client_logging_dir = Path(r"C:\proxy") / "client_logs"
endpoint_logging_dir = Path(r"C:\proxy") / "endpoints_logs"

if not server_logging_dir.exists():
    server_logging_dir.mkdir(parents=True, exist_ok=True)

if not client_logging_dir.exists():
    client_logging_dir.mkdir(parents=True, exist_ok=True)

if not endpoint_logging_dir.exists():
    endpoint_logging_dir.mkdir(parents=True, exist_ok=True)


def get_socket_server_logger() -> logging.Logger:
    """
    Returns logger using for socket server logging.
    """
    logger = logging.getLogger("socket_server")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s - lino: %(lineno)d", "%Y-%m-%d %H:%M:%S")
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
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s - lino: %(lineno)d", "%Y-%m-%d %H:%M:%S")
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
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "{client_ip} - {asctime} - {levelname} - {message} [module:{module}|func:{funcName}]",
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
