import datetime
from typing import Any, cast

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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from logs.logging_conf import get_endpoint_logger
from modems import router as modems_router
from modems import router_templates as modems_templates_router
from modems import router_ws as ws_router
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase
from starlette.templating import _TemplateResponse
from users import router as users_router
from users.models import User

templates = Jinja2Templates(directory="templates")
endpoint_logger = get_endpoint_logger()

settings = get_settings()

Base = cast(DeclarativeBase, Base)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    debug=settings.debug,
    title="Proxy Management",
    version="0.2",
)
start_time = datetime.datetime.now()


app.include_router(users_router.router, tags=["users"])
app.include_router(modems_router.router, tags=["modems"])
app.include_router(ws_router.router, tags=["modems"])
app.include_router(auth_api_router.router, tags=["auth"])
app.include_router(auth_templates_router.router, tags=["templates"])
app.include_router(modems_templates_router.router, tags=["templates"])


if settings.debug:
    app.mount("/static", StaticFiles(directory="static"), name="static")

if settings.use_root_path:
    app.root_path = "/api/v1"

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
    context: dict[str, Any] = {}

    user = cast(User, request.state.user) if request.state.user is not None else None

    if user is not None:
        context["user"] = user
        context["delete_user_url"] = build_full_endpoint_url(request, "delete_user", {"email": str(user.email)})
        context["modems_list_url"] = build_full_endpoint_url(request, "modems_list")
        context["logout_url"] = build_full_endpoint_url(request, "logout")
    else:
        context["login_url"] = build_full_endpoint_url(request, "login_page")

    if settings.cookies_google_access_token in request.cookies:
        context["google_disconnection_url"] = build_full_endpoint_url(request, "revoke_google_auth")

    return templates.TemplateResponse(request, name="index.html", context=context)


@app.get(
    "/health_check",
    status_code=status.HTTP_200_OK,
    response_class=JSONResponse,
    operation_id="health-check",
    description="Check server connection availability.",
    tags=["health-check"]
)
async def health_check(db: DatabaseDependency) -> JSONResponse:
    """
    Health check endpoint to monitor the server and database status.

    This endpoint performs a health check to verify the server's availability and
    status of its dependencies. It checks the following:

    - **Database connection**: Executes a simple query to confirm the database is reachable.
    - **Server uptime**: Calculates the server's uptime since its start.
    - **Application version**: Displays the current version of the application.
    - **Environment**: Indicates the environment (e.g., staging or production).

    Returns:
        JSONResponse: A JSON object with the following information:

        - `status` (str): Overall status of the server (always "ok" if reachable).
        - `database` (str): Status of the database connection, showing "connected" or
          an error message if there's an issue.
        - `uptime` (str): Uptime of the server in hours, minutes, and seconds.
        - `version` (str): Version of the application.
        - `environment` (str): Current environment in which the server is running (e.g., staging).

    Raises:
        Exception: If the database connection check fails, the error message is captured
        in the `database` status field.
    """
    db_status = "connected"
    try:
        db.execute(select(1))
    except Exception as e:
        db_status = f"Error: {str(e)}"

    current_time = datetime.datetime.now()
    uptime = current_time - start_time

    return JSONResponse(
        {
            "status": "ok",
            "database": db_status,
            "uptime": str(uptime),
            "version": app.version,
            "environment": "staging",
        },
        status.HTTP_200_OK,
    )
