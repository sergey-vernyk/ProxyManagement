from common.utils import build_full_endpoint_url
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
    name="signup",
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
        _TemplateResponse: Renders `registration.html`.
    """
    reg_url = build_full_endpoint_url(request, "registration")
    login_url = build_full_endpoint_url(request, "login_page")
    captcha_verify_url = build_full_endpoint_url(request, "captcha_verify")

    return templates.TemplateResponse(
        request,
        name="registration.html",
        context={
            "reg_url": reg_url,
            "login_url": login_url,
            "captcha_verify_url": captcha_verify_url,
            "cloudflare_sitekey": settings.cloudflare_turnstile_sitekey,
        },
    )


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
    compare_codes_url = build_full_endpoint_url(request, "compare_codes")
    repeat_compare_codes_url = build_full_endpoint_url(request, "send_verification_email")
    login_url = build_full_endpoint_url(request, "login_page")

    return templates.TemplateResponse(
        request,
        name="verify_otp.html",
        context={
            "login_url": login_url,
            "compare_codes_url": compare_codes_url,
            "repeat_compare_codes_url": repeat_compare_codes_url,
            "uid": uid,
            "token": token,
        },
    )


@router.get(
    "/users/login/",
    status_code=status.HTTP_200_OK,
    name="login_page",
    response_class=HTMLResponse,
    operation_id="Provides user login with the email and password or with Google Oauth2 flow.",
    responses={200: {"description": "Successful"}},
)
async def login_page(request: Request) -> _TemplateResponse:
    """
    Renders the user login page.

    Args:
        request (Request): Incoming HTTP request.

    Returns:
        _TemplateResponse: Renders `authentication.html`.
    """
    reg_url = build_full_endpoint_url(request, "signup")
    basic_login_url = build_full_endpoint_url(request, "basic_login")
    google_login_url = build_full_endpoint_url(request, "login_google")
    reset_password_page_url = build_full_endpoint_url(request, "reset_password_page")
    # email_verify_url = build_full_endpoint_url(request, "send_verification_email")
    captcha_verify_url = build_full_endpoint_url(request, "captcha_verify")

    return templates.TemplateResponse(
        request,
        name="authentication.html",
        context={
            "basic_login_url": basic_login_url,
            "google_login_url": google_login_url,
            "reg_url": reg_url,
            "reset_password_page_url": reset_password_page_url,
            "captcha_verify_url": captcha_verify_url,
            # "email_verify_url": email_verify_url,
            "cloudflare_sitekey": settings.cloudflare_turnstile_sitekey,
        },
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
        request (Request): HTTP request.

    Returns:
        _TemplateResponse: template `reset_password.html` with the reset password url link.
    """
    reset_password_url = build_full_endpoint_url(request, "reset_password")
    login_url = build_full_endpoint_url(request, "login_page")
    captcha_verify_url = build_full_endpoint_url(request, "captcha_verify")

    return templates.TemplateResponse(
        request,
        name="reset_password.html",
        context={
            "reset_password_url": reset_password_url,
            "login_url": login_url,
            "captcha_verify_url": captcha_verify_url,
            "cloudflare_sitekey": settings.cloudflare_turnstile_sitekey,
        },
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
            with the confirm reset password url link uid, token and login url.
    """
    reset_password_confirm_url = build_full_endpoint_url(request, "reset_password_confirm")
    login_url = build_full_endpoint_url(request, "login_page")

    return templates.TemplateResponse(
        request,
        name="reset_password_confirm.html",
        context={
            "login_url": login_url,
            "reset_password_confirm_url": reset_password_confirm_url,
            "uid": uid,
            "token": token,
        },
    )
