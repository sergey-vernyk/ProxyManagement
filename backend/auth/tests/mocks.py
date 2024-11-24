from datetime import datetime
from typing import Any, Callable, NoReturn

import httpx
from config import get_settings
from dependencies import DatabaseDependency
from fastapi import BackgroundTasks, Request, status
from google.auth.exceptions import GoogleAuthError

settings = get_settings()
# pylint: disable=missing-docstring
# pylint: disable=unused-argument

_GOOGLE_ISSUERS = ["accounts.google.com", "https://accounts.google.com"]


class GoogleRequestAdapter:
    def __init__(self, session=None):
        pass


class MockRequest:
    @property
    def query_params(self) -> dict[str, str]:
        return {"code": "jnofnoosdpcenfpqcpqefq"}


class MockHttpXAsyncClient:
    @staticmethod
    async def mock_post_google_login_success(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_200_OK,
            json={
                "access_token": "mock_access_token",
                "id_token": "mock_id_token",
                "expires_in": 3600,
            },
            request=request,
        )

    @staticmethod
    async def mock_post_no_access_token(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_200_OK,
            json={
                "id_token": "mock_id_token",
                "expires_in": 3600,
            },
            request=request,
        )

    @staticmethod
    async def mock_post_verify_cloudflare_captcha_success(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_200_OK,
            json={
                "success": True,
                "error_codes": [],
                "challenge_ts": datetime(year=2024, month=11, day=15, hour=8, minute=45, second=0).strftime(
                    "%Y-%m-%d %H:%M:%S.%"
                ),
                "hostname": "example.com",
            },
            request=request,
        )

    @staticmethod
    async def mock_post_verify_cloudflare_captcha_error(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            json={"success": False, "error-codes": ["invalid-input-response"]},
            request=request,
        )

    @staticmethod
    async def mock_post_no_id_token(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_200_OK,
            json={
                "access_token": "mock_access_token",
                "expires_in": 3600,
            },
            request=request,
        )

    @staticmethod
    async def mock_get_google_login_success_user_not_exists(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("GET", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_200_OK,
            json={"email": "john.smith@gmail.com"},
            request=request,
        )

    @staticmethod
    async def mock_get_google_login_success_user_exists(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("GET", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_200_OK,
            json={"email": "john.doe@gmail.com"},
            request=request,
        )

    @staticmethod
    async def mock_post_revoke_google_auth_success(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_200_OK,
            request=request,
        )


async def mock_send_otp_email_handler(
    bg_tasks: BackgroundTasks, request: Request, token: str, db: DatabaseDependency, uid: str | None = None
) -> None:
    return None


class MockBackgroundTasks:
    context: dict[str, str] = {}

    def mock_add_bg_task_reset_password(
        self, func: Callable[[str, dict[str, Any]], None], user_email: str, context: dict[str, Any]
    ) -> None:
        self.context = context
        return None


def mock_generate_random_otp(length: int = 8) -> str:
    return "12345678"


def mock_verify_oauth2_token_success(id_token: str, request: GoogleRequestAdapter, audience: str) -> dict[str, Any]:
    return {
        "iss": "https://accounts.google.com",
        "azp": "azp_value",
        "aud": "usd_value",
        "sub": "john.doe@gmail.com",
        "email_verified": True,
        "at_hash": "hash_value",
        "iat": "1732470911",
        "exp": "1732474511",
    }


def mock_verify_oauth2_token_invalid_issuer(id_token: str, request: GoogleRequestAdapter, audience: str) -> NoReturn:
    raise GoogleAuthError(f"Wrong issuer. 'iss' should be one of the following: {_GOOGLE_ISSUERS}")


def mock_verify_oauth2_token_verification_failed(
    id_token: str, request: GoogleRequestAdapter, audience: str
) -> NoReturn:
    raise ValueError("Value error occurred")
