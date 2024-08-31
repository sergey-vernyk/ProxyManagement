from typing import Any

from common.sending_email import EmailContent, email_sender


def send_verification_email(user_email: str, context: dict[str, Any]) -> None:
    """
    Send an email with the OTP to the `user_email`.

    Args:
        user_email (str): user email to send the OTP.
        context (dict[str, Any]): context which will be used in jinja template.
    """
    html_body = email_sender.render_to_string("email_verification.html", context)
    subject = "Email verification"
    content = EmailContent(html_name=html_body)

    email_sender.send_mail(send_to=user_email, subject=subject, content=content)
