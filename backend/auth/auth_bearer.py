from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from config import get_settings
from dependencies import DatabaseDependency
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from users.crud import get_user_by_email
from users.models import User
from users.schemas import UserRole

settings = get_settings()
security = HTTPBearer(scheme_name="OAuth JWT")


async def verify_google_id_token(
    db: DatabaseDependency, credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> None:
    """
    Verifies the provided Google ID token and checks if the associated email exists in the database.

    Args:
        db (DatabaseDependency): Dependency for interacting with the database.
        token (HTTPAuthorizationCredentials): The HTTP Bearer token retrieved from the request.

    Raises:
        HTTPException: Raised if the token is invalid, the issuer is invalid,
            or no user is found in the database.
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
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Token verification fails. Reason {e}.") from e
    except GoogleAuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"The token issuer is invalid. Reason {e}.") from e

    email: str = token_info.get("email", "")
    if email:
        db_user = get_user_by_email(db, email)
        if db_user is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token is not bind to any user.")


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

        This method is called to process the incoming request and perform JWT
        authentication. It checks if the Bearer token is present and valid
        and verifies the token against the database to ensure the user exists.

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
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid authentication credentials")

            if self.verify_jwt(credentials.credentials, db):
                return credentials.credentials

        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid authorization code.")

    def verify_jwt(self, token: str, db: Session) -> bool:
        """
        Verify the JWT token's validity and check if the user exists in the database.

        This method decodes the JWT token and retrieves the user email from
        the token's payload. It then checks the database to ensure that a user
        with the extracted email exists.

        Args:
            token (str): The JWT token to be verified.
            db (Session): The SQLAlchemy database session used to query the
                          database.

        Returns:
            bool: True if the token is valid and the user exists; False otherwise.

        Raises:
            HTTPException: If the token cannot be validated, or if the user
                           associated with the token does not exist.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            email = payload.get("sub")
            if email is None:
                raise credentials_exception

            user = db.query(User).filter(User.email == email, User.role == UserRole.ADMIN).first()
            if user is None:
                raise credentials_exception

        except (JWTError, ValidationError) as exc:
            raise credentials_exception from exc

        return True


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Returns generated jwt access token.
    """
    to_encode = data.copy()
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, key=settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt
