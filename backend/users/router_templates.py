from common.utils import get_base_url
from fastapi import APIRouter, status
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get(
    "/users/verify_email/{uid}/{token}",
    response_class=HTMLResponse,
    name="verify_email",
    status_code=status.HTTP_200_OK,
    operation_id="verify-user-email",
)
async def verify_email_page(request: Request, uid: str, token: str) -> _TemplateResponse:
    """
    HTTP GET endpoint to serve user's email verification page.
    User will be on the page, after following by URL in their email after registration.

    Args:
        request (Request): HTTP request.
        uid (str): user ID, encoded in base64_urlsafe format.
        token (str): user token which generates after user registration.

    Returns:
        _TemplateResponse: Renders the "verify_email.html" template.
    """
    base_url = get_base_url(request)

    compare_path = request.url_for("compare_codes").components.path
    repeat_path = request.url_for("send_verification_email").components.path

    compare_codes_url = f"{base_url}{compare_path}"
    repeat_compare_codes_url = f"{base_url}{repeat_path}"

    return templates.TemplateResponse(
        request,
        name="verify_otp.html",
        context={
            "compare_codes_url": compare_codes_url,
            "repeat_compare_codes_url": repeat_compare_codes_url,
            "uid": uid,
            "token": token,
        },
    )
