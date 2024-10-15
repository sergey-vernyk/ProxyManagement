from typing import cast

from auth import router_api as auth_api_router
from auth import router_templates as auth_templates_router
from common.decorators import template_jwt_verification
from common.utils import get_base_url
from config import get_settings
from db_connection import Base, engine
from dependencies import DatabaseDependency
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from modems import router as modems_router
from modems import router_templates as modems_templates_router
from sqlalchemy.orm import DeclarativeBase
from starlette.templating import _TemplateResponse
from users import router_api as users_api_router
from users import router_templates as users_templates_router

templates = Jinja2Templates(directory="templates")

settings = get_settings()

Base = cast(DeclarativeBase, Base)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Proxy Management",
    version="0.2",
)


app.include_router(users_api_router.router, tags=["users"])
app.include_router(modems_router.router, tags=["modems"])
app.include_router(auth_api_router.router, tags=["auth"])
app.include_router(auth_templates_router.router, tags=["templates"])
app.include_router(users_templates_router.router, tags=["templates"])
app.include_router(modems_templates_router.router, tags=["templates"])


app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_class=HTMLResponse,
    name="index",
)
@template_jwt_verification
async def index_page(request: Request, db: DatabaseDependency) -> _TemplateResponse:
    base_url = get_base_url(request)
    signup_path = request.url_for("signup").components.path
    signup_url = f"{base_url}{signup_path}"

    return templates.TemplateResponse(
        request,
        name="index.html",
        context={
            "user": request.state.user or None,
            "signup_url": signup_url,
        },
    )
