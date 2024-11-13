from typing import Any, Callable

import httpx
from dependencies import DatabaseDependency
from fastapi import BackgroundTasks, Request, status

# pylint: disable=missing-docstring
# pylint: disable=unused-argument


class MockRequest:
    @property
    def query_params(self) -> dict[str, str]:
        return {"code": "jnofnoosdpcenfpqcpqefq"}


class MockHttpXAsyncClient:
    @staticmethod
    async def mock_post(*args, **kwargs) -> httpx.Response:
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
    async def mock_get(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("GET", "http://testserver/some_endpoint")
        return httpx.Response(
            status_code=status.HTTP_200_OK,
            json={"email": "john.smith@gmail.com"},
            request=request,
        )


async def mock_send_otp_email_handler(
    bg_tasks: BackgroundTasks, request: Request, token: str, db: DatabaseDependency
) -> None:
    return None


class MockBackgroundTasks:
    context: dict[str, str] = {}

    def mock_add_bg_task_reset_password(
        self, func: Callable[[str, dict[str, Any]], None], user_email: str, context: dict[str, Any]
    ) -> None:
        self.context = context
        return None
