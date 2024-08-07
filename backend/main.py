from db_connection import Base, engine
from fastapi import FastAPI
from modems import router as modems_router
from users import router as users_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Proxy Management With Sockets", version="0.1")

app.include_router(users_router.router, tags=["users"])
app.include_router(modems_router.router, tags=["modems"])
