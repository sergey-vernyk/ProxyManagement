import os
import pathlib
from pathlib import Path

import click
import uvicorn
from dotenv import load_dotenv

# build path to the base directory of the package (proxy_management)
BASE_DIR = Path(__file__).resolve().parent.parent


@click.group(help="CLI provides functionality for running uvicorn server with parameters.")
def cli_web() -> None:
    """CLI entrypoint for web application."""


@click.command(help="Run the FastAPI server with the provided options.")
@click.option("--host", "-h", type=click.STRING, show_default=True, default="0.0.0.0", help="Server host.")
@click.option("--port", "-p", type=click.INT, show_default=True, default=8000, help="Server port.")
@click.option("--workers", type=click.INT, show_default=True, default=2, help="Number of worker processes.")
@click.option("--env-file", type=click.Path(exists=True), required=True, help="Environment configuration file.")
def runserver(workers: int, host: str, port: int, env_file: pathlib.Path) -> None:
    """
    Run the FastAPI server using uvicorn with the specified options.

    Args:
        workers (int): Number of worker processes for handling requests.
        env_file (pathlib.Path): Path to the environment configuration file.
        host (str): The server host address.
        port (int): The port to bind the server.

    This command sets up and runs the FastAPI server with configurable settings such as
    host, port, and workers. It also optionally reads an environment configuration file if specified.
    """
    load_dotenv(env_file, override=True)

    config = {
        "app": "proxy_management.main:app",
        "host": host,
        "port": port,
        "workers": workers,
    }

    # explicitly change directory to base which is 'proxy_management'
    os.chdir(BASE_DIR)
    uvicorn.run(**{key: value for key, value in config.items() if value is not None})


cli_web.add_command(runserver)
