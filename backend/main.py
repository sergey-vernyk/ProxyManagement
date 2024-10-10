from typing import cast

from auth import router_api as auth_api_router
from auth import router_templates as auth_templates_router
from config import get_settings
from db_connection import Base, engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from modems import router as modems_router
from sqlalchemy.orm import DeclarativeBase
from users import router_api as users_api_router
from users import router_templates as users_templates_router
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()

Base = cast(DeclarativeBase, Base)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Proxy Management With Sockets",
    version="0.1",
    swagger_ui_parameters={"persistAuthorization": True},
    swagger_ui_oauth2_redirect_url="/auth/callback"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your front-end URL in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

app.swagger_ui_init_oauth = {
    "clientId": settings.client_id,
    "clientSecret": settings.client_secret,  # Only necessary for some flows
    "usePkceWithAuthorizationCodeGrant": True,  # PKCE is recommended
    "scopes": "read:user",
    "authorizationUrl": "https://github.com/login/oauth/authorize",
    "tokenUrl": "https://github.com/login/oauth/access_token",
}

app.include_router(users_api_router.router, tags=["users"])
app.include_router(modems_router.router, tags=["modems"])
app.include_router(auth_api_router.router, tags=["auth"])
app.include_router(auth_templates_router.router, tags=["templates"])
app.include_router(users_templates_router.router, tags=["templates"])


app.mount("/static", StaticFiles(directory="static"), name="static")
