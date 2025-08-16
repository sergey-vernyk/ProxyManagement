from sqlalchemy.orm import Session

from . import models, schemas


def create_otp(db: Session, otp_data: schemas.CreateOTP) -> models.OTP:
    """Create OTP instance."""
    instance = models.OTP(user_id=otp_data.user_id, code=otp_data.code, expires_at=otp_data.expires_at)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance
