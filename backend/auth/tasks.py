from typing import Any

from common.sending_email import EmailContent, email_sender


def send_reset_password_email(user_email: str, context: dict[str, Any]) -> None:
    """
    Task sends an email with reset link to a user email.

    Args:
        user_email (str): email, which a user entered while requested password reset.
        context (dict[str, Any]): context that used in email.
    """
    html_body = email_sender.render_to_string("reset_password_email.html", context)
    subject = "Password reset"
    content = EmailContent(html=html_body)

    email_sender.send_mail(send_to=user_email, subject=subject, content=content)


def send_verification_email(user_email: str, context: dict[str, Any]) -> None:
    """
    Send an email with the OTP to the user email.

    Args:
        user_email (str): user email to send the OTP.
        context (dict[str, Any]): context which will be used in jinja template.
    """
    html_body = email_sender.render_to_string("email_verification.html", context)
    subject = "Email verification"
    content = EmailContent(html=html_body)

    email_sender.send_mail(send_to=user_email, subject=subject, content=content)
