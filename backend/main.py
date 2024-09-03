from auth import router_api as auth_api_router
from auth import router_templates as auth_templates_router
from db_connection import Base, engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from modems import router as modems_router
from users import router_api as users_api_router
from users import router_templates as users_templates_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Proxy Management With Sockets",
    version="0.1",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(users_api_router.router, tags=["users"])
app.include_router(modems_router.router, tags=["modems"])
app.include_router(auth_api_router.router, tags=["auth"])
app.include_router(auth_templates_router.router, tags=["templates"])
app.include_router(users_templates_router.router, tags=["templates"])


app.mount("/static", StaticFiles(directory="static"), name="static")
