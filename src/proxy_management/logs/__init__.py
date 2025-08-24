import os
import pathlib
import platform

from proxy_management.config import get_settings

OS = platform.system()

settings = get_settings()

ROOT_DIR = pathlib.Path()
server_logging_dir = pathlib.Path()
client_logging_dir = pathlib.Path()
endpoint_logging_dir = pathlib.Path()

if OS == "Linux":
    ROOT_DIR = pathlib.Path(os.path.expandvars(settings.root_dir_linux.format(os.environ.get("HOME"))))
elif OS == "Windows":
    ROOT_DIR = pathlib.Path(settings.root_dir_win)

if ROOT_DIR:
    server_logging_dir = ROOT_DIR / "server_logs"
    client_logging_dir = ROOT_DIR / "client_logs"
    endpoint_logging_dir = ROOT_DIR / "endpoints_logs"

if not server_logging_dir.exists():
    server_logging_dir.mkdir(parents=True, exist_ok=True)

if not client_logging_dir.exists():
    client_logging_dir.mkdir(parents=True, exist_ok=True)

if not endpoint_logging_dir.exists():
    endpoint_logging_dir.mkdir(parents=True, exist_ok=True)
