import os
import pathlib
import platform

from config import get_settings

settings = get_settings()
OS = platform.system()

ROOT_DIR = pathlib.Path()

if OS == "Linux":
    ROOT_DIR = pathlib.Path(os.path.expandvars(settings.root_dir_linux.format(os.environ.get("HOME"))))
elif OS == "Windows":
    ROOT_DIR = pathlib.Path(settings.root_dir_win)

ENCODING: str = settings.default_encoding
START_CONNECTION: bytes = settings.socket_start_connection_cond.encode(ENCODING)
STOP_CONNECTION: bytes = settings.socket_stop_connection_cond.encode(ENCODING)

if ROOT_DIR.exists():
    PID_FILE = ROOT_DIR / settings.pid_file
    CONN_COUNT_FILE = ROOT_DIR / settings.conn_count_file
