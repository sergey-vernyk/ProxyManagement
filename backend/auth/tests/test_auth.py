from base64 import urlsafe_b64encode
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import google.oauth2
import google.oauth2.id_token
import httpx
import pytest
import security
from auth import schemas
from auth.otp import utils
from auth.otp.models import OTP
from config import get_settings
from conftest import REGULAR_USER_DATA
from fastapi import BackgroundTasks, Request, status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pytest import MonkeyPatch
from sqlalchemy.orm import Session
from users.models import User

from ..schemas import EnteredCheckOTP, RegisterUser
from . import mocks

settings = get_settings()
dir_path = Path(__file__).parent.absolute()


# pylint: disable=missing-docstring
# pylint: disable=unused-argument


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
        monkeypatch.setattr(httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_google_login_success)
        monkeypatch.setattr(httpx.AsyncClient, "get", mocks.MockHttpXAsyncClient.mock_get_google_login_success)
        monkeypatch.setattr(Request, "query_params", mocks.MockRequest.query_params)

        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        # check whether a user was created if they authorized via Google for the first time
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
        monkeypatch.setattr(httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_google_login_success)
        monkeypatch.setattr(httpx.AsyncClient, "get", mocks.MockHttpXAsyncClient.mock_get_google_login_success)
        monkeypatch.setattr(Request, "query_params", {})

        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Missing code parameter."}

    def test_google_login_access_token_absent_in_response(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_no_access_token)
        monkeypatch.setattr(httpx.AsyncClient, "get", mocks.MockHttpXAsyncClient.mock_get_google_login_success)
        monkeypatch.setattr(Request, "query_params", mocks.MockRequest.query_params)

        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "No access token received."}

    def test_google_login_id_token_absent_in_response(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_no_id_token)
        monkeypatch.setattr(httpx.AsyncClient, "get", mocks.MockHttpXAsyncClient.mock_get_google_login_success)
        monkeypatch.setattr(Request, "query_params", mocks.MockRequest.query_params)

        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "No ID token received."}

    def test_revoke_google_auth_success(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Request, "cookies", mocks.MockRequestGoogleRevoke.cookies_jwt)
        monkeypatch.setattr(httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_revoke_google_auth_success)
        monkeypatch.setattr(google.oauth2.id_token, "verify_oauth2_token", mocks.mock_verify_oauth2_token_success)

        response = client.post("/auth/revoke/google", headers={"X-CSRFToken": "csrf_value"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "message": "Your Google account has been successfully disconnected from the application."
        }
        assert settings.cookies_key_csrf not in response.cookies
        assert settings.cookies_google_access_token not in response.cookies
        assert settings.cookies_key_jwt not in response.cookies

    def test_revoke_google_auth_user_not_authorized_via_google(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Request, "cookies", mocks.MockRequestGoogleRevoke.cookies_only_csrf)
        response = client.post("/auth/revoke/google", headers={"X-CSRFToken": "csrf_value"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "You are not authorized via Google."}

    def test_revoke_google_auth_invalid_token_issuer(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Request, "cookies", mocks.MockRequestGoogleRevoke.cookies_jwt)
        monkeypatch.setattr(httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_revoke_google_auth_success)
        monkeypatch.setattr(google.oauth2.id_token, "verify_oauth2_token", mocks.mock_verify_oauth2_token_invalid_issuer)
        response = client.post("/auth/revoke/google", headers={"X-CSRFToken": "csrf_value"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {
            "detail": "The token issuer is invalid: Wrong issuer. 'iss' should be one of "
            "the following: ['accounts.google.com', 'https://accounts.google.com']."
        }

    def test_revoke_google_auth_token_verification_failed(
        self, client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Request, "cookies", mocks.MockRequestGoogleRevoke.cookies_jwt)
        monkeypatch.setattr(httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_revoke_google_auth_success)
        monkeypatch.setattr(
            google.oauth2.id_token, "verify_oauth2_token", mocks.mock_verify_oauth2_token_verification_failed
        )
        response = client.post("/auth/revoke/google", headers={"X-CSRFToken": "csrf_value"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Token verification fails: Value error occurred."}


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


class TestUserAccountActions:
    """
    Testing actions with user account:
        - registration
        - activation
        - reset password
    """

    def test_register_user_success(
        self, client: TestClient, monkeypatch: MonkeyPatch, db: Session, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        user_data = RegisterUser(email="john.doe@gmail.com", password="strong_password")
        monkeypatch.setattr("auth.router_api.send_otp_email_handler", mocks.mock_send_otp_email_handler)
        response = client.post("/auth/registration", json=user_data.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Check your email for verifying your account."}
        registered_user = db.query(User).filter(User.email == user_data.email).first()
        assert registered_user is not None
        assert registered_user.is_verified is False
        assert str(registered_user.email) == user_data.email
        assert len(str(registered_user.token)) == settings.unique_user_token_length

    def test_register_user_invalid_email(self, client: TestClient, mock_build_ip_address_for_log: MonkeyPatch) -> None:
        with pytest.raises(ValidationError) as exc:
            RegisterUser(email="john.doe@gmail", password="strong_password")

        assert exc.value.errors() == [
            {
                "type": "value_error",
                "loc": ("email",),
                "msg": "value is not a valid email address: The part after the @-sign is not valid. It should have a period.",
                "input": "john.doe@gmail",
                "ctx": {"reason": "The part after the @-sign is not valid. It should have a period."},
            }
        ]

        user_data = RegisterUser(email="john.doe@example.com", password="strong_password")
        response = client.post("/auth/registration", json=user_data.model_dump())
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": {"email_invalid": "The domain name example.com does not accept email."}}

    def test_register_user_if_user_exists(
        self, client: TestClient, regular_user: User, mock_build_ip_address_for_log: MonkeyPatch
    ) -> None:
        user_data = RegisterUser(email=REGULAR_USER_DATA["email"], password="strong_password")
        response = client.post("/auth/registration", json=user_data.model_dump())
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": {"user_exists": "User with the given email is already registered."}}

    def test_reset_password_requesting_success(
        self,
        client: TestClient,
        monkeypatch: MonkeyPatch,
        regular_user: User,
        mock_build_ip_address_for_log: MonkeyPatch,
    ) -> None:
        mock_bg_tasks_inst = mocks.MockBackgroundTasks()
        monkeypatch.setattr(BackgroundTasks, "add_task", mock_bg_tasks_inst.mock_add_bg_task_reset_password)
        monkeypatch.setattr("auth.router_api.send_otp_email_handler", mocks.mock_send_otp_email_handler)

        data = schemas.ResetPassword(email=REGULAR_USER_DATA["email"])
        response = client.post("/auth/reset_password", json=data.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == "Email message with the link for password reset has been sent to your email."

    def test_reset_password_requesting_user_not_exists(
        self,
        client: TestClient,
        regular_user: User,
        mock_build_ip_address_for_log: MonkeyPatch,
    ) -> None:
        data = schemas.ResetPassword(email="jackie.chan@gmail.com")  # !user not exists with this email
        response = client.post("/auth/reset_password", json=data.model_dump())
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "User with the given email does not exist."}

    def test_reset_password_confirm_success(
        self,
        client: TestClient,
        monkeypatch: MonkeyPatch,
        regular_user: User,
        db: Session,
        mock_build_ip_address_for_log: MonkeyPatch,
    ) -> None:
        mock_bg_tasks_inst = mocks.MockBackgroundTasks()
        monkeypatch.setattr(BackgroundTasks, "add_task", mock_bg_tasks_inst.mock_add_bg_task_reset_password)
        monkeypatch.setattr("auth.router_api.send_otp_email_handler", mocks.mock_send_otp_email_handler)

        current_password = regular_user.hashed_password

        # make request for password reset
        data = schemas.ResetPassword(email=REGULAR_USER_DATA["email"])
        response = client.post("/auth/reset_password", json=data.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == "Email message with the link for password reset has been sent to your email."

        reset_link_parts = mock_bg_tasks_inst.context["reset_link"].split("/")
        uid, token = reset_link_parts[-2], reset_link_parts[-1]
        data = schemas.ResetPasswordConfirm(
            new_password="changed_password",
            confirm_password="changed_password",
            token=token,
            uid=uid,
        )
        # confirm password reset
        response = client.post("/auth/reset_password_confirm", json=data.model_dump())
        assert response.status_code == status.HTTP_200_OK
        db.refresh(regular_user)
        assert str(current_password) != str(regular_user.hashed_password)
        assert response.json() == "Password has been reset successfully."

    def test_reset_password_confirm_password_mismatch(
        self,
        client: TestClient,
        monkeypatch: MonkeyPatch,
        regular_user: User,
        mock_build_ip_address_for_log: MonkeyPatch,
    ) -> None:
        mock_bg_tasks_inst = mocks.MockBackgroundTasks()
        monkeypatch.setattr(BackgroundTasks, "add_task", mock_bg_tasks_inst.mock_add_bg_task_reset_password)
        monkeypatch.setattr("auth.router_api.send_otp_email_handler", mocks.mock_send_otp_email_handler)

        data = schemas.ResetPassword(email=REGULAR_USER_DATA["email"])
        response = client.post("/auth/reset_password", json=data.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == "Email message with the link for password reset has been sent to your email."

        reset_link_parts = mock_bg_tasks_inst.context["reset_link"].split("/")
        uid, token = reset_link_parts[-2], reset_link_parts[-1]
        data = schemas.ResetPasswordConfirm(
            new_password="changed_password",
            confirm_password="changed_password_123",
            token=token,
            uid=uid,
        )
        # confirm password reset
        response = client.post("/auth/reset_password_confirm", json=data.model_dump())
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Entered passwords are mismatch."}

    def test_reset_password_confirm_uid_or_token_invalid(
        self,
        client: TestClient,
        monkeypatch: MonkeyPatch,
        regular_user: User,
        mock_build_ip_address_for_log: MonkeyPatch,
    ) -> None:
        mock_bg_tasks_inst = mocks.MockBackgroundTasks()
        monkeypatch.setattr(BackgroundTasks, "add_task", mock_bg_tasks_inst.mock_add_bg_task_reset_password)
        monkeypatch.setattr("auth.router_api.send_otp_email_handler", mocks.mock_send_otp_email_handler)

        data = schemas.ResetPassword(email=REGULAR_USER_DATA["email"])
        response = client.post("/auth/reset_password", json=data.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == "Email message with the link for password reset has been sent to your email."

        reset_link_parts = mock_bg_tasks_inst.context["reset_link"].split("/")
        uid, token = reset_link_parts[-2], reset_link_parts[-1]
        # with pytest.raises(ValidationError) as exc:
        data = schemas.ResetPasswordConfirm(
            new_password="changed_password",
            confirm_password="changed_password",
            token="87jbiADAKZ1P6dfgJIAFF39zeYHUG123",  # !wrong token
            uid=uid,
        )
        response = client.post("/auth/reset_password_confirm", json=data.model_dump())
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Password reset link is invalid."}

        data = schemas.ResetPasswordConfirm(
            new_password="changed_password",
            confirm_password="changed_password",
            token=token,
            # !wrong uid (user with id 100 does not exist)
            uid=urlsafe_b64encode("100".encode(settings.default_encoding)).decode(settings.default_encoding),
        )
        response = client.post("/auth/reset_password_confirm", json=data.model_dump())
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Password reset link is invalid."}

    def test_compare_otp_codes_success(
        self,
        client: TestClient,
        db: Session,
        monkeypatch: MonkeyPatch,
        regular_user: User,
        mock_build_ip_address_for_log: MonkeyPatch,
    ) -> None:
        assert regular_user.is_verified is False
        monkeypatch.setattr(utils, "generate_random_otp", mocks.mock_generate_random_otp)
        utils.create_otp(db, int(regular_user.id))  # type: ignore
        hashed_entered_otp = security.generate_hashed_otp(mocks.mock_generate_random_otp())

        assert db.query(OTP).filter(OTP.code == hashed_entered_otp).first() is not None

        opt_schema = EnteredCheckOTP(
            entered_otp=mocks.mock_generate_random_otp(),
            uid=urlsafe_b64encode(str(regular_user.id).encode(settings.default_encoding)).decode(
                settings.default_encoding
            ),
            token=str(regular_user.token),
        )

        response = client.post("/auth/compare_codes/", json=opt_schema.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"success": "The code you entered is correct. Email has been verified."}
        assert regular_user.is_verified is True
        assert db.query(OTP).filter(OTP.code == hashed_entered_otp).first() is None

    def test_compare_otp_entered_code_incorrect(
        self,
        client: TestClient,
        db: Session,
        monkeypatch: MonkeyPatch,
        regular_user: User,
        mock_build_ip_address_for_log: MonkeyPatch,
    ) -> None:
        assert regular_user.is_verified is False
        monkeypatch.setattr(utils, "generate_random_otp", mocks.mock_generate_random_otp)
        utils.create_otp(db, int(regular_user.id))  # type: ignore
        hashed_entered_otp = security.generate_hashed_otp(mocks.mock_generate_random_otp())

        assert db.query(OTP).filter(OTP.code == hashed_entered_otp).first() is not None

        invalid_random_otp = "".join(list(reversed(mocks.mock_generate_random_otp())))  # !just reverse OTP
        opt_schema = EnteredCheckOTP(
            entered_otp=invalid_random_otp,
            uid=urlsafe_b64encode(str(regular_user.id).encode(settings.default_encoding)).decode(
                settings.default_encoding
            ),
            token=str(regular_user.token),
        )

        response = client.post("/auth/compare_codes/", json=opt_schema.model_dump())
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "The code you entered is incorrect."}
        assert regular_user.is_verified is False  # user is still unverified
        assert db.query(OTP).filter(OTP.code == hashed_entered_otp).first() is not None  # OTP is still exists in DB.

    def test_compare_otp_entered_code_expired(
        self,
        client: TestClient,
        db: Session,
        monkeypatch: MonkeyPatch,
        regular_user: User,
        mock_build_ip_address_for_log: MonkeyPatch,
    ) -> None:
        assert regular_user.is_verified is False
        monkeypatch.setattr(utils, "generate_random_otp", mocks.mock_generate_random_otp)
        utils.create_otp(db, int(regular_user.id))  # type: ignore
        hashed_entered_otp = security.generate_hashed_otp(mocks.mock_generate_random_otp())

        db_code = db.query(OTP).filter(OTP.code == hashed_entered_otp).first()
        assert db_code is not None

        # make otp expired
        setattr(db_code, "expires_at", datetime.now() - timedelta(hours=1))
        db.commit()
        db.refresh(db_code)

        opt_schema = EnteredCheckOTP(
            entered_otp=mocks.mock_generate_random_otp(),
            uid=urlsafe_b64encode(str(regular_user.id).encode(settings.default_encoding)).decode(
                settings.default_encoding
            ),
            token=str(regular_user.token),
        )

        response = client.post("/auth/compare_codes/", json=opt_schema.model_dump())
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "Code is expired."}
        assert regular_user.is_verified is False  # user is still unverified
        assert db.query(OTP).filter(OTP.code == hashed_entered_otp).first() is None


def test_verify_cloudflare_captcha_success(
    client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_verify_cloudflare_captcha_success
    )

    captcha_schema = schemas.CloudflareCaptcha(token="some_token", idempotency_key="some_key")
    response = client.post("/auth/verify_captcha", json=captcha_schema.model_dump())
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Success"}


def test_verify_cloudflare_captcha_token_not_provided(
    client: TestClient, monkeypatch: MonkeyPatch, mock_build_ip_address_for_log: MonkeyPatch
) -> None:
    monkeypatch.setattr(httpx.AsyncClient, "post", mocks.MockHttpXAsyncClient.mock_post_verify_cloudflare_captcha_error)
    captcha_schema = schemas.CloudflareCaptcha(token=None, idempotency_key="some_key")
    response = client.post("/auth/verify_captcha", json=captcha_schema.model_dump())
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"message": "Error", "error-codes": ["invalid-input-response"]}
