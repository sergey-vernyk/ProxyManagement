from email_validator import EmailNotValidError, ValidatedEmail, validate_email


def validate_email_format(email: str) -> str:
    """
    Function validates the given `email`, returns it, if it's valid
    or returns None otherwise.
    """
    try:
        email_instance: ValidatedEmail = validate_email(email)
        return email_instance.email
    except EmailNotValidError as e:
        raise ValueError(e) from e
