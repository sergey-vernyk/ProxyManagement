from typing import cast

from auth import router_api as auth_api_router
from auth import router_templates as auth_templates_router
from config import get_settings
from db_connection import Base, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from modems import router as modems_router
from sqlalchemy.orm import DeclarativeBase
from users import router_api as users_api_router
from users import router_templates as users_templates_router

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


app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
