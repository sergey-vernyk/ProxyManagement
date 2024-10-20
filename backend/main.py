from typing import cast

from auth import router_api as auth_api_router
from auth import router_templates as auth_templates_router
from common.decorators import template_jwt_verification
from common.utils import build_full_endpoint_url
from config import get_settings
from db_connection import Base, engine
from dependencies import DatabaseDependency
from exceptions import (ClientRequestError, EntityDoesNotExistError,
                        UserUnauthorizedError, custom_error_handler)
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from logs.logging_conf import get_endpoint_logger
from modems import router as modems_router
from modems import router_templates as modems_templates_router
from sqlalchemy.orm import DeclarativeBase
from starlette.templating import _TemplateResponse
from users import router as users_router

templates = Jinja2Templates(directory="templates")
endpoint_logger = get_endpoint_logger()

settings = get_settings()

Base = cast(DeclarativeBase, Base)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Proxy Management",
    version="0.2",
)


app.include_router(users_router.router, tags=["users"])
app.include_router(modems_router.router, tags=["modems"])
app.include_router(auth_api_router.router, tags=["auth"])
app.include_router(auth_templates_router.router, tags=["templates"])
app.include_router(modems_templates_router.router, tags=["templates"])


app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(
    exc_class_or_status_code=EntityDoesNotExistError,
    handler=custom_error_handler(
        status_code=status.HTTP_404_NOT_FOUND,
        initial_detail="Not Found",
        logger=endpoint_logger,
    ),
)

app.add_exception_handler(
    exc_class_or_status_code=ClientRequestError,
    handler=custom_error_handler(
        status_code=status.HTTP_400_BAD_REQUEST,
        initial_detail="Invalid client request",
        logger=endpoint_logger,
    ),
)

app.add_exception_handler(
    exc_class_or_status_code=UserUnauthorizedError,
    handler=custom_error_handler(
        status_code=status.HTTP_401_UNAUTHORIZED,
        initial_detail="Not authorized",
        logger=endpoint_logger,
    ),
)


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    description="Main page of the application.",
    operation_id="main-page",
    response_class=HTMLResponse,
    name="index",
    tags=["templates"],
)
@template_jwt_verification
async def index_page(request: Request, db: DatabaseDependency) -> _TemplateResponse:  # pylint: disable=W0613
    """
    The root (home) page.

    Args:
        request (Request): HTTP request.
        db (DatabaseDependency): Database session used for JWT verification.
            (its needed for @template_jwt_verification).

    Returns:
        _TemplateResponse: template `index.html` with the user instance,
            url for logout, login, modems which binds to the user instance and
            url for fully disconnecting google account from the application.
    """
    logout_url = build_full_endpoint_url(request, "logout")
    login_url = build_full_endpoint_url(request, "login_page")
    modems_list_url = build_full_endpoint_url(request, "modems_list")

    is_google_authentication = settings.cookies_google_access_token in request.cookies
    google_disconnection_url = None

    if is_google_authentication:
        google_disconnection_url = build_full_endpoint_url(request, "revoke_google_auth")

    return templates.TemplateResponse(
        request,
        name="index.html",
        context={
            "user": request.state.user if request.state.user is not None else None,
            "logout_url": logout_url,
            "login_url": login_url,
            "modems_list_url": modems_list_url,
            "google_disconnection_url": google_disconnection_url,
        },
    )
