from secrets import token_urlsafe

from common.utils import get_base_url
from config import get_settings
from fastapi import APIRouter, status
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse

templates = Jinja2Templates(directory="templates")
router = APIRouter()
settings = get_settings()


@router.get(
    "/users/signup/",
    status_code=status.HTTP_200_OK,
    response_class=HTMLResponse,
    operation_id="user-registration-page",
    description="Provides user registration with email and password.",
    responses={200: {"description": "Successful"}},
)
async def registration_page(request: Request) -> _TemplateResponse:
    """
    Renders the user registration page.

    Args:
        request (Request): Incoming HTTP request.

    Returns:
        _TemplateResponse: Renders `registration.html` with registration URL and OAuth URL.
    """
    base_url = get_base_url(request)
    reg_path = request.url_for("registration").components.path
    reg_url = f"{base_url}{reg_path}"

    return templates.TemplateResponse(
        request,
        name="registration.html",
        context={
            "reg_url": reg_url,
            "oauth_google_url": request.url_for("login_google"),
        },
    )


@router.get(
    "/users/success_signup/",
    status_code=status.HTTP_200_OK,
    response_class=HTMLResponse,
    name="success_registration_page",
    operation_id="user-registration-success-page",
    description="Redirect to this page after successful registration.",
    responses={200: {"description": "Successful"}},
)
async def success_registration_page(request: Request) -> _TemplateResponse:
    """
    Page which will be displayed after successful registration.

    Args:
        request (Request): HTTP request.

    Returns:
        _TemplateResponse: template `registration_success.html` with the message.
    """
    return templates.TemplateResponse(
        request,
        name="registration_success.html",
        context={"message": "Check your email for verifying your account."},
    )


@router.get(
    "/users/reset_password/",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    name="reset_password_page",
    operation_id="reset-password-page",
    description="Reset user password.",
    responses={200: {"description": "Successful"}},
)
async def reset_password_page(request: Request) -> _TemplateResponse:
    """
    Page which will be displayed form for enter user email for reset password.

    Args:
        request (Request): HTTP request

    Returns:
        _TemplateResponse: template `reset_password.html` with the reset password url link.
    """
    base_url = get_base_url(request)
    reset_password_path = request.url_for("reset_password").components.path
    reset_password_url = f"{base_url}{reset_password_path}"
    return templates.TemplateResponse(
        request,
        name="reset_password.html",
        context={"reset_password_url": reset_password_url},
    )


@router.get(
    "/users/reset_password_confirm/{uid}/{token}",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    name="reset_password_confirm_page",
    operation_id="reset-password-confirm-page",
    description="Confirm resetting user password after following the link in user email box.",
    responses={200: {"description": "Successful"}},
)
async def reset_password_confirm_page(request: Request, uid: str, token: str) -> _TemplateResponse:
    """
    A page that will display a form for entering passwords that will be compared.
    And if the passwords are the same, then this new password will be set for the user.

    Args:
        request (Request): HTTP request.
        uid (str): user ID encoded in base64_urlsafe format.
        token (str): user token.

    Returns:
        _TemplateResponse: template `reset_password_confirm.html`
            with the confirm reset password url link uid and token.
    """
    base_url = get_base_url(request)
    reset_password_confirm_path = request.url_for("reset_password_confirm").components.path
    reset_password_confirm_url = f"{base_url}{reset_password_confirm_path}"
    return templates.TemplateResponse(
        request,
        name="reset_password_confirm.html",
        context={
            "reset_password_confirm_url": reset_password_confirm_url,
            "uid": uid,
            "token": token,
        },
    )
