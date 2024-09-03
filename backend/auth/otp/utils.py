from base64 import urlsafe_b64encode
from datetime import datetime, timedelta

from common.utils import get_base_url
from config import get_settings
from fastapi import BackgroundTasks
from fastapi.requests import Request
from security import generate_hashed_otp, generate_random_otp
from sqlalchemy.orm import Session
from users.models import User

from ..tasks import send_verification_email
from .crud import create_otp as create_otp_crud
from .schemas import CreateOTP

settings = get_settings()
ENCODING = settings.default_encoding


def create_otp(db: Session, user_id: int) -> str:
    """
    Create OPT object with the created OTP plain string.

    Args:
        db (Session): database session.
        user_id (int): user ID for they the OTP will be created.

    Returns:
        str: OTP in plain format.
    """
    otp_code = generate_random_otp()
    otp_expires = datetime.now() + timedelta(minutes=settings.otp_expire_time)
    otp_data = CreateOTP(user_id=user_id, code=generate_hashed_otp(otp_code), expires_at=otp_expires)
    create_otp_crud(db, otp_data)
    return otp_code


async def send_otp_email_handler(
    bg_tasks: BackgroundTasks, request: Request, user_token: str, db: Session, uid: str | None = None
) -> None:
    """
    Create FastAPI background task for sending email with OTP to a user.

    Args:
        bg_tasks (BackgroundTasks): FastAPI background task implementation.
        request (Request): HTTP request.
        user_token (str): token assigned to the user.
        uid (str | None): encoded user ID in base64 format.
            Can be None if the user requests another one OTP,
            if the received OTP is expired or not correct.
        db (Session): database session.
    """
    base_url = get_base_url(request)
    user = db.query(User).filter(User.token == user_token).first()

    if user is not None:
        if uid is None:
            uid = urlsafe_b64encode(str(user.id).encode(ENCODING)).decode(ENCODING)
        verification_path = request.url_for("verify_email", uid=uid, token=user_token).components.path
        verification_url = f"{base_url}{verification_path}"
        bg_tasks.add_task(
            send_verification_email,
            str(user.email),
            context={
                "email": str(user.email),
                "otp_code": create_otp(db, user.id),  # type: ignore
                "verification_url": verification_url,
                "otp_expire_time": settings.otp_expire_time,
            },
        )
