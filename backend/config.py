from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PARENT_DIR_PATH = str(Path(__file__).resolve().parent)


class Settings(BaseSettings):
    """
    Class for environment settings environment variables.
    """

    default_encoding: str
    database_url: str
    socket_host: str
    socket_port: int
    socket_stop_connection_cond: str
    socket_start_connection_cond: str

    model_config = SettingsConfigDict(env_file=f"{PARENT_DIR_PATH}/.env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """
    Returns settings which creates only once.
    """
    return Settings()  # type: ignore
