from urllib.parse import parse_qs, urlparse

from config import get_settings
from conftest import REGULAR_USER_DATA
from fastapi import status
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from users.models import User

settings = get_settings()


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


def test_google_auth_redirect(client: TestClient) -> None:
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
