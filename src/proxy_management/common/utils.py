import inspect
from types import ModuleType
from typing import Any

from fastapi import Request


def get_base_url(request: Request) -> str:
    """
    Returns base URL depends on the port and scheme.

    Args:
        request (Request): HTTP request.

    Returns:
        str: base url like:
            - non-standard port:
                http://example.com:1234 or https://example.com:1234.
            - standard port:
                http://example.com or https://example.com.
    Raises:
        ValueError:
            if port and (or) host is not provided (None).
    """
    host = request.base_url.hostname
    port = request.headers.get("X-Forwarded-Port", request.base_url.port)
    scheme = request.headers.get("X-Forwarded-Proto", request.base_url.scheme)

    if port is not None and host is not None:
        if int(port) in {80, 443}:
            return f"{scheme}://{host}"

        return f"{scheme}://{host}:{port}"

    raise ValueError("Port and host for base url must not be None.")


def build_full_endpoint_url(request: Request, endpoint_name: str, params: dict[str, str] | None = None) -> str:
    """
    Builds full url to an API endpoint.

    Args:
        request (Request): HTTP request.
        endpoint_name (str): name of the API endpoint for which
            full URL will be built.
        params (dict[str, str]): path params for the endpoint. Default to None.

    Returns:
        str: full URL to an endpoint in format:
            - http://example.com/login/google
            - https://example.com/login/google
    """
    if params is None:
        params = {}

    base_url = get_base_url(request)
    endpoint_path = request.url_for(endpoint_name, **params).components.path
    return f"{base_url}{endpoint_path}"


def get_caller_info() -> dict[str, Any]:
    """
    Retrieves the function and module name of the caller.

    Returns:
        dict[str, Any]: A dictionary containing `func_name` and `module_name` keys,
            representing the name of the calling function and its module.
    """
    frame: inspect.FrameInfo = inspect.stack()[1]
    module: ModuleType | None = inspect.getmodule(frame[0])
    return {
        "func_name": frame.function,
        "module_name": module.__name__ if module is not None else None,
    }
