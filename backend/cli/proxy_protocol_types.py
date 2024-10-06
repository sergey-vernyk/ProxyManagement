from typing import Literal

import click
from db_connection import engine
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .schemas import EnvPathOrEnvUrl
from .utils import fetch_env_file, load_env_in_memory, load_env_in_shell_env


@click.group(help="CLI for creating different connection protocol types for proxy (http, socks, ftp, etc.).")
@click.option(
    "--env-file",
    type=click.STRING,
    required=True,
    help="Location of the environment configuration file.",
)
@click.option(
    "--username",
    "-u",
    type=click.STRING,
    required=False,
    help="Username for authenticating if the provided 'env_file' is URL.",
)
@click.option(
    "--password",
    "-pass",
    type=click.STRING,
    required=False,
    help="Password for authenticating if the provided 'env_file' is URL.",
)
@click.pass_context
def cli_proxy_protocols(ctx: click.Context, env_file: str, username: str | None, password: str | None) -> None:
    """
    CLI entrypoint for creating different connection protocol types
    for proxy (http, socks, ftp, etc.)

    Loads the environment variables from the provided file.

    Args:
        ctx (click.Context): Click context object for passing information across commands.
        env_file (str): Path to the environment configuration file.
        username (str | None): Username for authentication if the env_file is a URL.
        password (str | None): Password for authentication if the env_file is a URL.
    """
    ctx.ensure_object(dict)
    try:
        path_or_url = EnvPathOrEnvUrl(env_file_or_url=env_file)
    except ValidationError as e:
        click.echo(f"Invalid input: {e}")
        ctx.obj["ENV_VALID"] = False
        return

    ctx.obj["ENV_VALID"] = True
    if "http" in path_or_url.env_file_or_url:
        if username is None or password is None:
            click.echo(
                click.style(
                    "Username and password must be provided if param 'env_file' is URL.",
                    bold=True,
                    fg="red",
                )
            )
            raise click.Abort()

        env_file_content = fetch_env_file(path_or_url.env_file_or_url, username, password)
        load_env_in_memory(env_file_content)
    else:
        load_env_in_shell_env(env_file)


@click.command(
    help=(
        "Create one line for protocol in the proxy conf file "
        "(e.g. proxy -n -a -p49153 -i192.168.1.105 -e192.168.8.100)"
    )
)
@click.argument("users", type=click.STRING)
@click.option(
    "--anonymous",
    "-a",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enables anonymous proxy mode (no authentication required).",
)
@click.option(
    "--dns-resolve",
    "-n",
    is_flag=True,
    default=False,
    show_default=True,
    help="Disables DNS resolving.",
)
@click.option(
    "--protocol",
    "-p",
    type=click.Choice(["proxy", "socks", "ftppr", "pop3p", "smtpp", "dns", "tcppm", "udppm"], case_sensitive=False),
    show_choices=True,
    required=True,
    help="Proxy protocol.",
)
def create_connection_protocol(
    users: str,
    protocol: Literal["proxy", "socks", "ftppr", "pop3p", "smtpp", "dns", "tcppm", "udppm"],
    anonymous: bool,
    dns_resolve: bool,
) -> None:
    """
    Generates configuration lines for a proxy based on the specified users, protocol, and options.

    The command reads user information from the database and constructs one line of proxy configuration
    for each user, outputting it in the format:

        {protocol} [-n] [-a] -p{port} -i{internal_server_ip} -e{ip} # user: {email}

    where:
        - 'protocol' is the type of proxy to be used (e.g., "proxy", "socks", etc.).
        - '-n' disables DNS resolving if the '--dns-resolve' option is passed.
        - '-a' enables anonymous mode if the '--anonymous' option is passed.
        - '-p' specifies the port of the proxy service.
        - '-i' specifies the internal server IP to bind to.
        - '-e' specifies the external IP used for outgoing traffic.

    Args:
        users (str): A comma-separated string of user emails to generate proxy config lines for.
        protocol (Literal): The protocol type for the proxy
            (e.g., proxy, socks, ftppr, pop3p, smtpp, dns, tcppm, udppm).
        anonymous (bool): If set, enables anonymous mode (no authentication required).
        dns_resolve (bool): If set, disables DNS resolving.

    Returns:
        None: Outputs the proxy configuration line(s) to stdout.
    """
    # pylint: disable=C0415
    # pylint: disable=W0611
    from auth.otp.models import OTP
    from modems.models import Modem
    from users.models import User

    users_emails = users.split(",")
    try:
        with Session(engine) as session:
            users_ids_subquery = select(User.id).where(User.email.in_(users_emails)).subquery()
            modems_info = session.execute(
                select(Modem.ip, Modem.internal_server_ip, Modem.port, User.email)
                .join(User, Modem.bind_user_id == User.id)
                .where(Modem.bind_user_id.in_(users_ids_subquery.c.values()))
                .order_by(User.email)
            ).fetchall()
    except SQLAlchemyError as e:
        click.echo(click.style(f"Database error: {e}", fg="red", bold=True))
        return

    if not modems_info:
        click.echo(
            click.style(
                f"No modems found for the specified users: {', '.join(users_emails)}",
                fg="red",
            )
        )
        return

    result: list[list[str]] = []
    for ip, internal_server_ip, port, email in modems_info:
        line: list[str] = [protocol]
        if dns_resolve:
            line.append("-n")
        if anonymous:
            line.append("-a")

        line.extend([f"-p{port}", f"-i{internal_server_ip}", f"-e{ip}", f"  # user: {email}"])
        result.append(line)

    for prot in result:
        click.echo(" ".join(prot))


cli_proxy_protocols.add_command(create_connection_protocol)
