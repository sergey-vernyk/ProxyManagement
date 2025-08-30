import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV_PATH = Path(__file__).resolve().parent / ".env"
CURRENT_ENV_PATH = os.environ.get("ENV_FILE_PATH")


class Settings(BaseSettings):
    """
    Class with settings for environment variables.
    """

    debug: bool
    use_root_path: bool
    default_encoding: str

    # variables for JWT encoding and decoding without OAuth flow
    access_token_expire_seconds: int
    secret_key: str
    algorithm: str

    database_url: str
    database_url_test: str
    db_echo_enable: bool = True

    # variables for socket server and client
    socket_stop_connection_cond: str
    socket_start_connection_cond: str

    # variables for rebooting modem
    max_time_curl: int
    fetch_ip_attempts: int
    reboot_attempts: int
    delay_after_reboot: int

    # variables for logging
    max_bytes_log_rotating: int = 100_048_576  # 1Mb
    backup_count: int = 10
    root_dir_win: str
    root_dir_linux: str

    # variables for nginx conf
    domain: str
    server_port: int

    # email sending
    email_password: str
    email_host: str
    email_from_user: str
    email_port: int
    email_from: str

    # email verification
    otp_expire_time: int  # minutes

    # socket
    pid_file: str
    conn_count_file: str

    # Google OAuth
    google_client_id: str
    google_client_secret: str

    unique_user_token_length: int = 32

    # name of the key in cookies for persisting access JWT
    cookies_key_jwt: str
    cookies_google_access_token: str

    # CSRF
    cookies_key_csrf: str
    csrf_number_of_bytes: int

    # Cloudflare Captcha widget
    cloudflare_turnstile_secret_key: str
    cloudflare_turnstile_sitekey: str

    if DEFAULT_ENV_PATH.exists() or CURRENT_ENV_PATH and Path(CURRENT_ENV_PATH).exists():
        model_config = SettingsConfigDict(env_file=CURRENT_ENV_PATH or DEFAULT_ENV_PATH, env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """
    Returns settings which creates only once.
    """
    return Settings()  # type: ignore
