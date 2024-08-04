from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .db_connection import engine
from .dependencies import get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def root(db: Session = Depends(get_db)):
    return {"message": "hello"}
    