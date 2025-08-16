from typing import Annotated, Any, cast

import httpx
from fastapi import APIRouter, Path, Request, status
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse

from common.decorators import template_jwt_verification
from common.utils import build_full_endpoint_url
from dependencies import DatabaseDependency
from users.models import User

from . import models

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get(
    "/modems/{token}/{hashed_value}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    operation_id="change-ip-page",
    description="Provides possibility to change a modem IP address by rebooting the modem.",
    responses={200: {"description": "Successful"}},
)
@template_jwt_verification
async def change_ip_page(
    request: Request,
    db: DatabaseDependency,
    token: Annotated[str, Path(max_length=32, min_length=32, description="User token")],
    hashed_value: Annotated[str, Path(max_length=32, min_length=32, description="Modem hashed value")],
) -> _TemplateResponse:
    """
    HTTP GET endpoint to serve the modem IP change page.

    Parameters:
    - request (Request): The request object, containing information about the incoming request.
    - token (str): A 32-character string representing the user's token. Used to verify the user.
    - hashed_value (str): A 32-character string representing the hashed value of the modem. Used to identify the modem.
    - db (DatabaseDependency): The database session used to query modem data.

    Returns:
    - _TemplateResponse: Renders the "change_ip.html" template with WebSocket connection details.

    Flow:
    1. Query the database to find the modem associated with the provided `token` and `hashed_value`.
    2. Determine if the link is valid based on whether the modem is found.
    3. Extract the hostname, port, and schema (HTTP/HTTPS) from the request's base URL.
    4. Construct the appropriate WebSocket root URL (`ws_root_url`).
    5. Render the "change_ip.html" template, passing the constructed `ws_root_url`, `token`, `hashed_value`,
       `link_is_valid`, the current authenticated `user` and `logout_url` to the template context.
    """
    modem = (
        db.query(models.Modem)
        .join(User)
        .filter(
            models.Modem.hashed_value == hashed_value,
            User.token == token,
        )
        .first()
    )

    ws_url = build_full_endpoint_url(request, "change_ip").replace("http", "ws", 1)
    logout_url = build_full_endpoint_url(request, "logout")
    user: User = cast(User, request.state.user)

    return templates.TemplateResponse(
        request,
        name="change_ip.html",
        context={
            "link_is_valid": modem is not None,
            "modem_id": modem.id if modem is not None else None,
            "ws_root_url": ws_url,
            "token": token,
            "hashed_value": hashed_value,
            # variables necessary for 'base.html' template
            "user": user if user is not None else None,
            "logout_url": logout_url,
        },
    )


@router.get(
    "/modems/list/",
    response_model=None,
    name="modems_list",
    status_code=status.HTTP_200_OK,
    operation_id="modems-list-page",
    description="Provides list with modems of a user with additional data.",
    responses={200: {"description": "Successful"}},
)
@template_jwt_verification
async def modems_list_page(request: Request, db: DatabaseDependency) -> _TemplateResponse:  # pylint: disable=unused-argument
    """
    Fetches and renders a list of user modems with additional data.

    Args:
        request (Request): The HTTP request object containing user info.
        db (DatabaseDependency): The database connection dependency.

    Returns:
        _TemplateResponse: Renders the template with modem data and user context.
    """
    authenticated_user: User = request.state.user
    proxies_list_endpoint = build_full_endpoint_url(
        request,
        "change_ip_urls",
        {"email": authenticated_user.email},
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(proxies_list_endpoint)
        proxies_reboot_data: list[dict[str, Any]] = response.json()

    logout_url = build_full_endpoint_url(request, "logout")
    return templates.TemplateResponse(
        request,
        name="proxies.html",
        context={
            "proxies_reboot_data": proxies_reboot_data,
            "user": authenticated_user,
            "logout_url": logout_url,
        },
    )
