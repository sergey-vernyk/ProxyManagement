from typing import Any, Generator, cast

import logs.logging_conf
import pytest
from config import get_settings
from db_connection import Base
from dependencies import get_db
from fastapi.testclient import TestClient
from main import app
from security import get_password_hash
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from users import models, schemas

REGULAR_USER_DATA = {
    "email": "john.doe@gmail.com",
    "password": "strong_password",
    "proxy_password_plain": "proxy_password",
}

settings = get_settings()

SQLALCHEMY_DATABASE_URL = settings.database_url_test


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, Any, None]:
    """
    Create database and tables in it, yield this database,
    and remove all tables after all tests will be executed.
    """
    engine: Engine = create_engine(SQLALCHEMY_DATABASE_URL)
    db_base = cast(DeclarativeBase, Base)
    with engine.connect() as connection:
        db_base.metadata.create_all(bind=engine)
        connection.begin()

    yield engine

    with engine.connect() as connection:
        connection.rollback()
        engine.dispose()
        db_base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_engine: Engine) -> Generator[Any, Any, None]:  # pylint: disable=W0621
    """
    Returns session for test database and close database connection
    after all test will be executed.

    Args:
        db_engine(Engine): database engine instance.
    """
    with db_engine.begin() as connection:
        test_db = Session(bind=connection, expire_on_commit=False)

        yield test_db

        test_db.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[Any, Any, None]:  # pylint: disable=W0621
    """
    Override dependency for using test database instead of main database
    and create test client for testing API.

    Args:
        db(Session): SQLAlchemy database session.
    """
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app=app, base_url="http://test/") as c:
        yield c

    c.close()


@pytest.fixture
def mock_build_ip_address_for_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Mocks function `build_ip_address_for_log` which must receive
    real IP address, but test client always returns `testclient` value.

    Args:
        monkeypatch (pytest.MonkeyPatch): patch fixture.
    """
    monkeypatch.setattr(logs.logging_conf, "build_ip_address_for_log", lambda _: "192.168.x.x")


@pytest.fixture
def regular_user(db: Session) -> Generator[models.User, Any, None]:  # pylint: disable=W0621
    """
    Creates regular user instance.

    Args:
        db(Session): SQLAlchemy database session.
    """
    user_schema = schemas.CreateRegularUser(
        email=REGULAR_USER_DATA["email"],
        proxy_password_plain=REGULAR_USER_DATA["proxy_password_plain"],
        password=REGULAR_USER_DATA["password"],
    )

    user = models.User(
        **user_schema.model_dump(exclude={"password"}),
        hashed_password=get_password_hash(user_schema.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
