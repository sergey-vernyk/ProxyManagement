from urllib.parse import parse_qs, urlparse

import httpx
from config import get_settings
from conftest import REGULAR_USER_DATA
from fastapi import Request, status
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session
from users.models import User

settings = get_settings()


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


class TestBasicAuth:
    """
    Testing basic authentication with the given user email and password.
    After successful authentication, created JWT and CSRF tokens will be saved into Cookies.
    """

    def test_login_success(
        self, client: TestClient, regular_user: User, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        response = client.post(
            url="/auth/login",
            data={"email": str(regular_user.email), "password": REGULAR_USER_DATA["password"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "redirect_url" in response.json()
        assert response.json()["redirect_url"] == str(client.base_url)
        assert settings.cookies_key_jwt in response.cookies
        assert settings.cookies_key_csrf in response.cookies

    def test_login_invalid_email(
        self, client: TestClient, regular_user: User, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        response = client.post(
            url="/auth/login",
            data={"email": "john.doe@example.com", "password": REGULAR_USER_DATA["password"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": {"email_invalid": "The domain name example.com does not accept email."}}

        response = client.post(
            url="/auth/login",
            data={"email": "john.doe@example", "password": REGULAR_USER_DATA["password"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "email"],
                    "msg": "value is not a valid email address: The part after the @-sign is not valid. It should have a period.",
                    "input": "john.doe@example",
                    "ctx": {"reason": "The part after the @-sign is not valid. It should have a period."},
                }
            ]
        }

    def test_login_user_not_found(
        self, client: TestClient, regular_user: User, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        response = client.post(
            url="/auth/login",
            data={"email": "john@gmail.com", "password": REGULAR_USER_DATA["password"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": {"user_not_exists": "User with the given email does not exist."}}

    def test_login_invalid_password(
        self, client: TestClient, regular_user: User, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        response = client.post(
            url="/auth/login",
            data={"email": str(regular_user.email), "password": "wrong_password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": {"incorrect_email_or_password": "Incorrect email or password."}}


class TestGoogleAuth:
    def test_google_login_success(
        self, client: TestClient, db: Session, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(httpx.AsyncClient, "post", MockHttpXAsyncClient.mock_post)
        monkeypatch.setattr(httpx.AsyncClient, "get", MockHttpXAsyncClient.mock_get)
        monkeypatch.setattr(Request, "query_params", MockRequest.query_params)

        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        # check wheter a user was created if they authorized via Google for the first time
        assert db.query(User).filter(User.email == "john.smith@gmail.com").first() is not None
        assert response.headers["Location"] == str(client.base_url)
        assert settings.cookies_key_jwt in response.cookies
        assert settings.cookies_key_csrf in response.cookies
        assert settings.cookies_google_access_token in response.cookies

    def test_google_auth_redirect(self, client: TestClient) -> None:
        response = client.get("/auth/login/google", follow_redirects=False)

        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT

        redirect_url = response.headers["Location"]
        parsed_url = urlparse(redirect_url)
        query_params: dict[str, list[str]] = parse_qs(parsed_url.query)

        # Check the expected parameters in the query
        assert parsed_url.netloc == "accounts.google.com"
        assert parsed_url.path == "/o/oauth2/auth"
        assert "client_id" in query_params
        assert "redirect_uri" in query_params
        assert "state" in query_params
        assert "access_type" in query_params
        assert "response_type" in query_params
        assert "scope" in query_params
        assert "include_granted_scopes" in query_params

    def test_google_login_authorization_code_not_provided(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(httpx.AsyncClient, "post", MockHttpXAsyncClient.mock_post)
        monkeypatch.setattr(httpx.AsyncClient, "get", MockHttpXAsyncClient.mock_get)
        monkeypatch.setattr(Request, "query_params", {})

        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Missing code parameter."}

    def test_google_login_access_token_absent_in_response(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(httpx.AsyncClient, "post", MockHttpXAsyncClient.mock_post_no_access_token)
        monkeypatch.setattr(httpx.AsyncClient, "get", MockHttpXAsyncClient.mock_get)
        monkeypatch.setattr(Request, "query_params", MockRequest.query_params)

        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "No access token received."}

    def test_google_login_id_token_absent_in_response(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(httpx.AsyncClient, "post", MockHttpXAsyncClient.mock_post_no_id_token)
        monkeypatch.setattr(httpx.AsyncClient, "get", MockHttpXAsyncClient.mock_get)
        monkeypatch.setattr(Request, "query_params", MockRequest.query_params)

        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "No ID token received."}


def test_logout_success(client: TestClient, mock_build_ip_address_for_log: MonkeyPatch) -> None:
    client.cookies.set(settings.cookies_google_access_token, "google_token")
    client.cookies.set(settings.cookies_key_jwt, "access_token")
    client.cookies.set(settings.cookies_key_csrf, "csrf_token")

    response = client.post("/auth/logout")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": "You are successfully logged out.",
        "redirect_url": f"{client.base_url}users/login/",
    }
    assert response.cookies.get(settings.cookies_google_access_token) is None
    assert response.cookies.get(settings.cookies_key_jwt) is None
    assert response.cookies.get(settings.cookies_key_csrf) is None


def test_logout_user_already_unauthorized(client: TestClient, mock_build_ip_address_for_log: MonkeyPatch) -> None:
    client.cookies.set(settings.cookies_google_access_token, "google_token")
    client.cookies.set(settings.cookies_key_csrf, "csrf_token")

    response = client.post("/auth/logout")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "You are not authorized."}
    assert response.cookies.get(settings.cookies_google_access_token) is None
    assert response.cookies.get(settings.cookies_key_jwt) is None
    assert response.cookies.get(settings.cookies_key_csrf) is None
