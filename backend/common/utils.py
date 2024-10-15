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


def build_full_endpoint_url(request: Request, endpoint_name: str) -> str:
    """
    Builds full url to an API endpoint.

    Args:
        request (Request): HTTP request.
        endpoint_name (str): name of the API endpoint for which
            full URL will be built.

    Returns:
        str: full URL to an endpoint in format:
            - http://example.com/login/google
            - https://example.com/login/google
    """
    base_url = get_base_url(request)
    endpoint_path = request.url_for(endpoint_name).components.path
    return f"{base_url}{endpoint_path}"
