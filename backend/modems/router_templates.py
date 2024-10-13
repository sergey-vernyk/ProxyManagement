from typing import Annotated

from common.utils import get_base_url
from dependencies import DatabaseDependency
from fastapi import APIRouter, Path, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse
from users.models import User

from . import models

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get(
    "/modems/{token}/{hashed_value}",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    operation_id="change-ip-page",
    description="Provides possibility to change a modem IP address by rebooting the modem.",
    responses={200: {"description": "Successful"}},
)
async def change_ip_page(
    request: Request,
    token: Annotated[str, Path(max_length=32, min_length=32, description="User token")],
    hashed_value: Annotated[str, Path(max_length=32, min_length=32, description="Modem hashed value")],
    db: DatabaseDependency,
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
       and `link_is_valid` to the template context.
    """
    modem = (
        db.query(models.Modem).join(User).filter(models.Modem.hashed_value == hashed_value, User.token == token).first()
    )
    link_is_valid = modem is not None

    http_base_url = get_base_url(request)
    ws_path = request.url_for("change_ip").components.path
    ws_base_url = http_base_url.replace("http", "ws", 1)

    return templates.TemplateResponse(
        request,
        name="change_ip.html",
        context={
            "link_is_valid": link_is_valid,
            "modem_id": modem.id if modem is not None else None,
            "ws_root_url": f"{ws_base_url}{ws_path}",
            "token": token,
            "hashed_value": hashed_value,
        },
    )
