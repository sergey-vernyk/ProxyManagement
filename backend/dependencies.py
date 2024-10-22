from secrets import compare_digest
from typing import Annotated, Any, Generator, NoReturn

from common.utils import get_caller_info
from config import get_settings
from db_connection import SessionLocal
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from logs.logging_conf import build_logger_extra_data, get_endpoint_logger
from pydantic import ValidationError
from sqlalchemy.orm import Session
from users import crud, models

logger = get_endpoint_logger()
settings = get_settings()
security = HTTPBearer(
    scheme_name="JWT Authorization",
    description="JSON Web Token authorization with Google OAuth or token generating with PyJWT.",
)


def get_db() -> Generator[Session, Any, None]:
    """
    Creates a new SQLAlchemy Session instance
    that will be used in a single request.
    """
    with SessionLocal() as db:
        yield db


DatabaseDependency = Annotated[Session, Depends(get_db)]


class JWTBearer(HTTPBearer):
    """
    A security class to handle JWT Bearer token authentication.

    This implements custom logic for JWT (JSON Web Token) authentication.
    It ensures that the incoming request contains a valid Bearer token
    and provides functionality to verify the token's validity.

    Args:
        auto_error (bool): Whether to automatically raise HTTP errors if
                           authentication fails. Defaults to True.
    """

    def __init__(self, auto_error: bool = True) -> None:
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request, db: DatabaseDependency) -> str:
        """
        Extract and validate the Bearer token from the request.

        Args:
            request (Request): The incoming HTTP request containing the
                               authorization header.
            db (Session): The SQLAlchemy database session used to query the
                          database.

        Returns:
            str: The valid JWT token if authentication is successful.

        Raises:
            HTTPException: If the authentication scheme is not 'Bearer',
                           or if the token is invalid or the user is not found.
        """
        credentials: HTTPAuthorizationCredentials | None = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid authentication credentials.")

            if await self.verify_jwt(credentials.credentials, db):
                return credentials.credentials

        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid authorization code.")

    async def verify_jwt(self, token: str, db: Session) -> models.User:
        """
        Verify the JWT token's validity and check if the user exists in the database.

        Args:
            token (str): The JWT token to be verified.
            db (Session): The SQLAlchemy database session used to query the
                          database.

        Returns:
            models.User: current authenticated user.

        Raises:
            HTTPException: If the token cannot be validated, or if the user
                           associated with the token does not exist.
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            email = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "User email is not present in JWT claims.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user = db.query(models.User).filter(models.User.email == email).first()
            if user is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Token is not bind to any user.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        except (JWTError, ValidationError) as exc:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        return user


async def verify_google_id_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> models.User:
    """
    Verifies the provided Google ID token and checks if the associated email exists in the database.

    Args:
        db (DatabaseDependency): Dependency for interacting with the database.
        token (HTTPAuthorizationCredentials): The HTTP Bearer token retrieved from the request.

    Raises:
        HTTPException: Raised if the token is invalid, the issuer is invalid,
            or no user is found in the database.

    Returns:
        models.User: current authenticated user.

    """
    if credentials.scheme != "Bearer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid authentication credentials.")

    try:
        token_info: dict[str, Any] = id_token.verify_oauth2_token(
            credentials.credentials,
            requests.Request(),
            settings.google_client_id,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Token verification fails: {e}.") from e
    except GoogleAuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"The token issuer is invalid: {e}.") from e

    email: str = token_info.get("email", "")
    if email:
        db_user = crud.get_user_by_email(db, email)
        if db_user is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token is not bind to any user.")

    return db_user


async def jwt_verification(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> models.User:
    """
    Verifies the provided authentication credentials
    by checking both Google ID tokens and JWT tokens.

    The function attempts to verify the Google ID token first, followed by the JWT token.

    Args:
        db (Session): The SQLAlchemy database session used to query the database.
        credentials (HTTPAuthorizationCredentials): The HTTP Bearer token retrieved from the request.

    Returns:
        models.User: current authenticated user.

    Raises:
        HTTPException: Raises a 401 Unauthorized error if both verifications fail,
                       including details about the errors encountered during the process.
    """
    exceptions: list[HTTPException] = []
    try:
        return await verify_google_id_token(credentials, db)
    except HTTPException as e:
        exceptions.append(e)

    try:
        jwt_bearer = JWTBearer()
        return await jwt_bearer.verify_jwt(credentials.credentials, db)
    except HTTPException as e:
        exceptions.append(e)

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        {"errors": [exc.detail for exc in exceptions]},
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_csrf_token(
    request: Request,
    cookie_token: str = Cookie(
        default=None,
        include_in_schema=False,
        alias="csrftoken",
    ),
    header_token: str = Header(
        default=None,
        convert_underscores=False,
        include_in_schema=False,
        alias="X-CSRFToken",
    ),
) -> None:
    """
    Verifies the CSRF tokens provided by the client in the request's cookie and header.

    Args:
        cookie_token (str): CSRF token extracted from the client's `csrftoken` cookie.
        header_token (str): CSRF token extracted from the `X-CSRFToken` header.

    Raises:
        HTTPException: Raised with HTTP 403 status if the tokens are missing or do not match.
    """

    def raise_csrf_error(detail: str) -> NoReturn:
        logger.error(
            detail,
            extra={**build_logger_extra_data(request), **get_caller_info()},
        )
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail,
        )

    if not header_token:
        raise_csrf_error("CSRF token is missing in Headers.")

    if not cookie_token:
        raise_csrf_error("CSRF token is missing in Cookies.")

    from_header_bytes = header_token.encode(settings.default_encoding)
    from_cookie_bytes = cookie_token.encode(settings.default_encoding)

    if not compare_digest(from_header_bytes, from_cookie_bytes):
        raise_csrf_error("CSRF token is incorrect.")


CsrfVerifyDependency = Depends(verify_csrf_token)
