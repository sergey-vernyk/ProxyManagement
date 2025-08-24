from fastapi import Response


def set_cookie(response: Response, key: str, value: str, http_only: bool = True, max_age: int = 3600) -> None:
    """
    Create cookie from `key` and `value`.

    Args:
        response (Response): HTTP response.
        key (str): key, which holds cookies value.
        value (str): cookie value.
        http_only (bool): define, whether the cookie value can be read using JavaScript.
        max_age (int): time to live for the value in the Cookies. Default to 3600 seconds.
    """
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=http_only,
        secure=True,
        samesite="lax",
    )


def delete_cookie(response: Response, key: str) -> None:
    """
    Remove cookie from client side by `key`.

    Args:
        response (Response): HTTP request.
        key (str): key, by which the cookie will be removed.
    """
    response.delete_cookie(key=key, secure=True, httponly=True, samesite="strict")
