from fastapi import Response


def set_cookie(response: Response, key: str, value: str) -> None:
    """
    Create cookie from `key` and `value`.

    Args:
        response (Response): HTTP response.
        key (str): key, which holds cookies value.
        value (str): cookie value.
    """
    response.set_cookie(
        key=key,
        value=value,
        max_age=3600,
        httponly=True,
        secure=True,
        samesite="strict",
    )


def delete_cookie(response: Response, key: str) -> None:
    """
    Remove cookie from client side by `key`.

    Args:
        response (Response): HTTP request.
        key (str): key, by which the cookie will be removed.
    """
    response.delete_cookie(key=key, secure=True, httponly=True, samesite="strict")
